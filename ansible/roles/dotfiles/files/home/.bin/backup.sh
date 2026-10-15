#!/bin/bash
# Backup script for rsync-over-SSH remote backups
set -eu

# --- Verbose option ---
VERBOSE=false
CLEAN_PACKAGES=false
for argument in "$@"; do
    case "$argument" in
        -v|--verbose) VERBOSE=true ;;
        --clean-packages) CLEAN_PACKAGES=true ;;
        *)
            printf 'Usage: %s [-v|--verbose] [--clean-packages]\n' "$0" >&2
            exit 2
            ;;
    esac
done

# --- Configuration ---
# shellcheck source=/etc/os-release
. /etc/os-release

CURRENT_HOSTNAME="$(hostnamectl hostname)"
REMOTE_HOST="pads918.home.lan"
REMOTE_USER="$(id -un)"
REMOTE_BASE_PATH="/volume1/NetBackup/${CURRENT_HOSTNAME}"

# Ensure SSH keys are loaded in the agent
if ! ssh-add -l >/dev/null 2>&1; then
    printf '\033[0;31mERROR: No SSH keys loaded in agent.\033[0m\n' >&2
    exit 1
fi

# SSH ControlMaster — reuses a single authenticated connection
# across all ssh/rsync calls, avoiding repeated handshakes.
SSH_CONTROL_SOCKET="${XDG_RUNTIME_DIR:-/tmp}/backup-ssh-${REMOTE_HOST}-$$"

# Wrapper: run ssh with consistent options
run_ssh() {
    ssh -o StrictHostKeyChecking=accept-new \
        -o ControlMaster=auto \
        -o "ControlPath=${SSH_CONTROL_SOCKET}" \
        -o ControlPersist=60 \
        "$@"
}

cleanup_ssh() {
    run_ssh -O exit "${REMOTE_USER}@${REMOTE_HOST}" 2>/dev/null || true
}
trap cleanup_ssh EXIT

# Open master connection once
run_ssh -fN "${REMOTE_USER}@${REMOTE_HOST}"

DOTFILES_REPOSITORY="${DOTFILES_REPOSITORY:-${HOME}/.dotfiles}"
TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"

# Package list paths
DIST_DIR="${DOTFILES_REPOSITORY}/dist/${ID}"
mkdir -p "${DIST_DIR}"
PKGLIST_OLD="$(ls -1 "${DIST_DIR}"/pkglist-*.txt 2>/dev/null | tail -1 || true)"
PKGLIST_CURRENT="${DIST_DIR}/pkglist-${TIMESTAMP}-${ID}.txt"

# Rsync SSH command string (no arrays in POSIX sh)
RSYNC_SSH="ssh -o StrictHostKeyChecking=accept-new \
    -o ControlMaster=auto -o ControlPath=${SSH_CONTROL_SOCKET} \
    -o ControlPersist=60"

if [ "$VERBOSE" = true ]; then
    RSYNC_INFO=("--info=progress2,name1,stats2" --itemize-changes)
else
    RSYNC_INFO=("--info=progress2,name0,stats2")
fi

# --- Colours & logging ---
C_ORANGE='\033[0;33m'
C_GREEN='\033[0;32m'
C_NC='\033[0m'

log() { printf "${2:-${C_NC}}%s${C_NC}\n" "$1"; }

# --- Remote size & formatting ---
get_remote_size() {
    local size
    size="$(run_ssh "${REMOTE_USER}@${REMOTE_HOST}" "du -s \"${REMOTE_BASE_PATH}\" 2>/dev/null" 2>/dev/null || true)"
    if [ -n "$size" ]; then
        printf '%s\n' "$size" | awk '{print $1}'
    else
        echo "0"
    fi
}

format_size() {
    local size_kb="$1"
    local prefix=""
    local abs_size_kb="$size_kb"
    if [ "$size_kb" -lt 0 ]; then
        abs_size_kb=$(( -size_kb ))
        prefix="-"
    else
        prefix="+"
    fi

    if [ "$abs_size_kb" -lt 1024 ]; then
        printf '%s%s KB\n' "$prefix" "$abs_size_kb"
    elif [ "$abs_size_kb" -lt 1048576 ]; then
        printf '%s%.2f MB\n' "$prefix" "$(echo "$abs_size_kb" | awk '{print $1 / 1024}')"
    else
        printf '%s%.2f GB\n' "$prefix" "$(echo "$abs_size_kb" | awk '{print $1 / 1048576}')"
    fi
}

format_volume() {
    awk -v bytes="$1" 'BEGIN {
        unit = "B"
        if (bytes >= 1073741824) {
            bytes /= 1073741824
            unit = "GB"
        } else if (bytes >= 1048576) {
            bytes /= 1048576
            unit = "MB"
        } else if (bytes >= 1024) {
            bytes /= 1024
            unit = "KB"
        }
        printf "%.2f %s\n", bytes, unit
    }'
}

decode_rsync_name() {
    local input="$1"
    local output=""
    local octal char
    local i=0
    local LC_ALL=C

    while [ "$i" -lt "${#input}" ]; do
        char="${input:i:1}"
        if [ "$char" = "\\" ]; then
            octal="${input:i+2:3}"
            if [ "${input:i:2}" = '\#' ] && [[ "$octal" =~ ^[0-7]{3}$ ]]; then
                output+="\\${octal}"
                i=$((i + 5))
            else
                output+="\\\\"
                i=$((i + 1))
            fi
        else
            output+="$char"
            i=$((i + 1))
        fi
    done

    printf -v RSYNC_DECODED_NAME '%b' "$output"
}

quote_remote_arg() {
    local input="$1"
    local output="'"
    local char
    local i

    for ((i = 0; i < ${#input}; i++)); do
        char="${input:i:1}"
        if [ "$char" = "'" ]; then
            output+="'\\''"
        else
            output+="$char"
        fi
    done

    output+="'"
    printf '%s' "$output"
}

remote_file_sizes() {
    local remote_dir="$1"
    shift
    local -a paths=("$@")
    local remote_path quoted_args command output kind bytes
    local start=0 index end

    while [ "$start" -lt "${#paths[@]}" ]; do
        end=$((start + 16))
        [ "$end" -le "${#paths[@]}" ] || end="${#paths[@]}"
        quoted_args=""
        for ((index = start; index < end; index++)); do
            remote_path="${remote_dir}/${paths[index]}"
            quoted_args+=" $(quote_remote_arg "$remote_path")"
        done

        command="LC_ALL=C stat -c '%F|%s' --${quoted_args}"
        if ! output="$(run_ssh "${REMOTE_USER}@${REMOTE_HOST}" "$command")"; then
            log "ERROR: Could not read sizes of files scheduled for deletion." "$C_ORANGE" >&2
            return 1
        fi

        while IFS='|' read -r kind bytes; do
            [ -n "$bytes" ] || continue
            if ! [[ "$bytes" =~ ^[0-9]+$ ]]; then
                log "ERROR: Invalid remote file size while preparing backup summary." "$C_ORANGE" >&2
                return 1
            fi
            if [ "$kind" != "directory" ]; then
                DELETED_BYTES=$((DELETED_BYTES + bytes))
            fi
        done <<< "$output"

        start="$end"
    done
}

collect_rsync_volumes() {
    local src="$1"
    local full_dest_path="$2"
    local exclude_file="$3"
    local plan_file="$4"
    local item size path
    local -a deleted_paths=()

    if ! rsync --dry-run --force --archive --perms --xattrs \
        --no-specials --no-devices --no-links \
        --delete --delete-excluded \
        -e "$RSYNC_SSH" \
        --itemize-changes --out-format='%i|%l|%n' \
        --exclude-from="$exclude_file" \
        "$src" "${REMOTE_USER}@${REMOTE_HOST}:${full_dest_path}/" > "$plan_file"; then
        return 1
    fi

    while IFS='|' read -r item size path; do
        case "$item" in
            '*deleting'*)
                decode_rsync_name "$path"
                deleted_paths+=("$RSYNC_DECODED_NAME")
                if [ "${#deleted_paths[@]}" -ge 16 ]; then
                    if ! remote_file_sizes "$full_dest_path" "${deleted_paths[@]}"; then
                        VOLUME_STATS_AVAILABLE=false
                    fi
                    deleted_paths=()
                fi
                ;;
            '>f+++++++++'|'<f+++++++++')
                if [[ "$size" =~ ^[0-9]+$ ]]; then
                    ADDED_BYTES=$((ADDED_BYTES + size))
                fi
                ;;
            '>f'*|'<f'*)
                if [[ "$size" =~ ^[0-9]+$ ]]; then
                    MODIFIED_BYTES=$((MODIFIED_BYTES + size))
                fi
                ;;
        esac
    done < "$plan_file"

    if [ "${#deleted_paths[@]}" -gt 0 ] && [ "$VOLUME_STATS_AVAILABLE" = true ]; then
        if ! remote_file_sizes "$full_dest_path" "${deleted_paths[@]}"; then
            VOLUME_STATS_AVAILABLE=false
        fi
    fi
}

ADDED_BYTES=0
DELETED_BYTES=0
MODIFIED_BYTES=0
VOLUME_STATS_AVAILABLE=true

# --- OS maintenance ---
manage_packages() {
    local id_check="${ID_LIKE:-$ID}"
    log "Checking packages ($id_check)..." "$C_ORANGE"

    case "$id_check" in
        *arch*)
            # pacman -Qtdq exits 1 when no orphans — suppress with || true
            orphans="$(pacman -Qtdq 2>/dev/null || true)"
            if [ -n "$orphans" ]; then
                log "Orphan packages detected (left installed):" "$C_ORANGE"
                printf '%s\n' "$orphans"
            fi
            if [ "$CLEAN_PACKAGES" = true ]; then
                yay -Sc --noconfirm
            fi
            pacman -Qqe | awk '{print $1}' > "${PKGLIST_CURRENT}"
            ;;
        *debian*)
            if [ "$CLEAN_PACKAGES" = true ]; then
                sudo apt autoremove --purge -y
            fi
            dpkg --get-selections '*' > "${PKGLIST_CURRENT}"
            ;;
    esac
}

manage_diffs() {
    if [ -n "${PKGLIST_OLD}" ] && [ -s "${PKGLIST_OLD}" ]; then
        local diff_file="${DIST_DIR}/pkglist-${TIMESTAMP}.diff"
        diff -U 0 "${PKGLIST_OLD}" "${PKGLIST_CURRENT}" > "${diff_file}" || true
        if [ -s "${diff_file}" ]; then
            log "Package list changes:" "$C_ORANGE"
            cat "${diff_file}"
        else
            rm -f "${diff_file}"
        fi
        rm -f "${PKGLIST_OLD}"
    fi
}

# --- Backup function ---
perform_rsync() {
    local src="$1"
    local subfolder="$2"
    local full_dest_path="${REMOTE_BASE_PATH}/${subfolder}"

    log "--- Syncing $src → ${REMOTE_HOST}:${full_dest_path} ---" "$C_ORANGE"

    run_ssh "${REMOTE_USER}@${REMOTE_HOST}" "mkdir -p \"${full_dest_path}\""

    # Collect all exclude sources into a temp file
    local exclude_tmp
    exclude_tmp="$(mktemp)"
    local plan_tmp
    plan_tmp="$(mktemp)"

    [ -f "${HOME}/.no_backup.txt" ] && cat "${HOME}/.no_backup.txt" >> "$exclude_tmp"
    dotfiles_dist="${DOTFILES_REPOSITORY}/dist"
    for f in "$dotfiles_dist"/*_excludes.txt; do
        [ -f "$f" ] && cat "$f" >> "$exclude_tmp"
    done

    if ! collect_rsync_volumes "$src" "$full_dest_path" "$exclude_tmp" "$plan_tmp"; then
        VOLUME_STATS_AVAILABLE=false
        log "WARNING: Could not estimate rsync change volumes." "$C_ORANGE" >&2
    fi
    rm -f "$plan_tmp"

    local rsync_rc=0
    if rsync --force --archive --perms --xattrs \
        --no-specials --no-devices --no-links \
        --delete --delete-excluded \
        -e "$RSYNC_SSH" \
        "${RSYNC_INFO[@]}" \
        --exclude-from="$exclude_tmp" \
        "${src}" "${REMOTE_USER}@${REMOTE_HOST}:${full_dest_path}/"; then
        :
    else
        rsync_rc=$?
    fi

    rm -f "$exclude_tmp"
    return "$rsync_rc"
}

# --- Execution ---
manage_packages
manage_diffs

START="$(date +%s)"
SIZE_BEFORE="$(get_remote_size)"

perform_rsync "${HOME}/" "home/${REMOTE_USER}"
perform_rsync "/etc/" "etc"

SIZE_AFTER="$(get_remote_size)"
DELTA=$(( SIZE_AFTER - SIZE_BEFORE ))

FINISH="$(date +%s)"
log "Backup completed in $(( (FINISH - START) / 60 ))m $(( (FINISH - START) % 60 ))s" "$C_GREEN"
if [ "$VOLUME_STATS_AVAILABLE" = true ]; then
    log "Estimated volume added: $(format_volume "$ADDED_BYTES")" "$C_GREEN"
    log "Estimated volume deleted: $(format_volume "$DELETED_BYTES")" "$C_GREEN"
    log "Estimated volume modified (new file sizes): $(format_volume "$MODIFIED_BYTES")" "$C_GREEN"
else
    log "Change volume summary unavailable." "$C_ORANGE"
fi
log "Disk space delta: $(format_size "$DELTA")" "$C_GREEN"
