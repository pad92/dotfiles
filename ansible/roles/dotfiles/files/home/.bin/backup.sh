#!/bin/bash
# Backup script for rsync-over-SSH remote backups.
#
# Usage: backup.sh [-v|--verbose] [--clean-packages] [--force-delete]
#                  [--max-deletions=N]
#
# Environment:
#   BACKUP_MAX_DELETIONS  deletion threshold (default 1000, 0 = no limit)
#   BACKUP_OS_RELEASE     os-release file to read (default /etc/os-release)
#   DOTFILES_REPOSITORY   repository holding dist/ (default ~/.dotfiles)
#
# Behaviour:
#   - A missing or empty source is refused.
#   - rsync status 24 (vanished files) only warns; any other failure is
#     reported at the end, both sources still run, and the exit status is the
#     worst one.
#   - /etc is read without root: unreadable files give status 23, and rsync
#     then skips deletions for that source.
#   - Replaced or deleted files are not kept on the NAS (--backup-dir would
#     need its own pruning), -x is not used because it would skip btrfs
#     subvolumes, and --partial is not used so an interrupted run never leaves
#     a half-written file under its final name.
#   - --clean-packages runs `yay -Sc` on Arch or `sudo apt autoremove --purge`
#     on Debian; --max-deletions=N skips a source whose dry run plans more
#     than N deletions; --force-delete lifts that limit.
#
# Exit status: 0 on success (rsync warning 24, "files vanished", is only
# reported); 2 on a usage error; otherwise the worst failure of the run.
set -euo pipefail

DEFAULT_MAX_DELETIONS=1000
DELETE_BATCH_SIZE=16

# --- Colours & logging ---
C_RED='\033[0;31m'
C_ORANGE='\033[0;33m'
C_GREEN='\033[0;32m'
C_NC='\033[0m'

log() { printf "${2:-${C_NC}}%s${C_NC}\n" "$1"; }

# --- Temporary files and cleanup ---
TEMP_PATHS=()
SSH_CONTROL_DIR=""
SSH_CONTROL_SOCKET=""

new_temp_file() {
    local path
    path="$(mktemp)"
    TEMP_PATHS+=("$path")
    NEW_TEMP_PATH="$path"
}

cleanup() {
    local path
    if [ -n "$SSH_CONTROL_SOCKET" ]; then
        run_ssh -O exit "${REMOTE_USER}@${REMOTE_HOST}" 2>/dev/null || true
    fi
    for path in "${TEMP_PATHS[@]}"; do
        rm -f -- "$path"
    done
    if [ -n "$SSH_CONTROL_DIR" ]; then
        rm -rf -- "$SSH_CONTROL_DIR"
    fi
}

# --- SSH ---
# Wrapper: run ssh with consistent options. -n keeps ssh from reading the
# caller's stdin (it would swallow the plan file read by a "while read" loop);
# nothing here is interactive, hence BatchMode.
run_ssh() {
    ssh -n \
        -o BatchMode=yes \
        -o StrictHostKeyChecking=accept-new \
        -o ServerAliveInterval=30 \
        -o ServerAliveCountMax=4 \
        -o ControlMaster=auto \
        -o "ControlPath=${SSH_CONTROL_SOCKET}" \
        -o ControlPersist=60 \
        "$@"
}

# The command string rsync runs for its transport. It must keep stdin (no -n).
build_rsync_ssh() {
    RSYNC_SSH="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
-o ServerAliveInterval=30 -o ServerAliveCountMax=4 \
-o ControlMaster=auto -o \"ControlPath=${SSH_CONTROL_SOCKET}\" \
-o ControlPersist=60"
}

# --- Validation ---
# Names end up in a remote path: accept only a plain, safe component.
is_safe_name() {
    [[ "$1" =~ ^[A-Za-z0-9_][A-Za-z0-9._-]*$ ]]
}

validate_identity() {
    : "${CURRENT_HOSTNAME:?hostname is empty}"
    : "${REMOTE_USER:?remote user is empty}"
    if ! is_safe_name "$CURRENT_HOSTNAME"; then
        log "ERROR: Unsafe hostname '${CURRENT_HOSTNAME}'." "$C_RED" >&2
        return 1
    fi
    if ! is_safe_name "$REMOTE_USER"; then
        log "ERROR: Unsafe user name '${REMOTE_USER}'." "$C_RED" >&2
        return 1
    fi
}

# --- Remote size & formatting ---
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

# Prints the size in KB of the remote backup tree: 0 when it does not exist
# yet, nothing and status 1 when the answer is not a number.
get_remote_size() {
    local size
    size="$(run_ssh "${REMOTE_USER}@${REMOTE_HOST}" \
        "du -s -- $(quote_remote_arg "$REMOTE_BASE_PATH") 2>/dev/null" 2>/dev/null || true)"
    size="${size%%[[:space:]]*}"
    if [ -z "$size" ]; then
        echo "0"
    elif [[ "$size" =~ ^[0-9]+$ ]]; then
        echo "$size"
    else
        return 1
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

# rsync escapes unusual bytes in %n as \#NNN (octal). Result in
# RSYNC_DECODED_NAME. The escapes become \xHH for printf %b, which, unlike
# a bare \NNN, decodes every byte value; other backslashes stay literal.
decode_rsync_name() {
    local input="$1"
    local output=""
    local octal char hex
    local i=0
    local LC_ALL=C

    while [ "$i" -lt "${#input}" ]; do
        char="${input:i:1}"
        if [ "$char" = "\\" ]; then
            octal="${input:i+2:3}"
            if [ "${input:i:2}" = '\#' ] && [[ "$octal" =~ ^[0-7]{3}$ ]]; then
                printf -v hex '\\x%02x' "$((8#$octal))"
                output+="$hex"
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

remote_file_sizes() {
    local remote_dir="$1"
    shift
    local -a paths=("$@")
    local remote_path quoted_args command output kind bytes
    local start=0 index end

    while [ "$start" -lt "${#paths[@]}" ]; do
        end=$((start + DELETE_BATCH_SIZE))
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

# Dry run: fills PLAN_DELETIONS and the ADDED/DELETED/MODIFIED byte counters.
# rsync 23 (partial transfer) and 24 (vanished files) still leave a usable plan.
collect_rsync_volumes() {
    local src="$1"
    local full_dest_path="$2"
    local exclude_file="$3"
    local plan_file="$4"
    local item size path plan_rc=0
    local -a deleted_paths=()

    PLAN_DELETIONS=0
    rsync --dry-run --force --archive --xattrs \
        --no-specials --no-devices \
        --delete --delete-excluded \
        -e "$RSYNC_SSH" \
        --itemize-changes --out-format='%i|%l|%n' \
        --exclude-from="$exclude_file" \
        "$src" "${REMOTE_USER}@${REMOTE_HOST}:${full_dest_path}/" > "$plan_file" || plan_rc=$?
    case "$plan_rc" in
        0|23|24) ;;
        *) return 1 ;;
    esac

    # The plan is read on fd 3, so nothing run in the loop can consume it.
    exec 3< "$plan_file"
    while IFS='|' read -r -u 3 item size path; do
        case "$item" in
            '*deleting'*)
                PLAN_DELETIONS=$((PLAN_DELETIONS + 1))
                decode_rsync_name "$path"
                deleted_paths+=("$RSYNC_DECODED_NAME")
                if [ "${#deleted_paths[@]}" -ge "$DELETE_BATCH_SIZE" ]; then
                    if [ "$VOLUME_STATS_AVAILABLE" = true ] \
                        && ! remote_file_sizes "$full_dest_path" "${deleted_paths[@]}"; then
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
    done
    exec 3<&-

    if [ "${#deleted_paths[@]}" -gt 0 ] && [ "$VOLUME_STATS_AVAILABLE" = true ]; then
        if ! remote_file_sizes "$full_dest_path" "${deleted_paths[@]}"; then
            VOLUME_STATS_AVAILABLE=false
        fi
    fi
}

# --- OS maintenance ---
# Writes the installed-package list to PKGLIST_CURRENT through a temporary
# file, so a failing command never leaves a truncated list. Sets
# PKGLIST_OK=true only for a complete, non-empty list.
manage_packages() {
    local id_check="${ID_LIKE:-${ID:-}}"
    local orphans tmp_list
    PKGLIST_OK=false
    log "Checking packages ($id_check)..." "$C_ORANGE"

    tmp_list="${PKGLIST_CURRENT}.tmp.$$"
    TEMP_PATHS+=("$tmp_list")

    case "$id_check" in
        *arch*)
            # pacman -Qtdq exits 1 when no orphans: suppress with || true
            orphans="$(pacman -Qtdq 2>/dev/null || true)"
            if [ -n "$orphans" ]; then
                log "Orphan packages detected (left installed):" "$C_ORANGE"
                printf '%s\n' "$orphans"
            fi
            pacman -Qqe | awk '{print $1}' > "$tmp_list" || : > "$tmp_list"
            ;;
        *debian*)
            dpkg --get-selections '*' > "$tmp_list" || : > "$tmp_list"
            ;;
        *)
            log "Package list skipped: unsupported distribution '${id_check}'." "$C_ORANGE"
            return 0
            ;;
    esac

    if [ -s "$tmp_list" ] && mv -- "$tmp_list" "$PKGLIST_CURRENT"; then
        PKGLIST_OK=true
    else
        log "WARNING: Could not build the package list; the previous one is kept." "$C_ORANGE" >&2
    fi
}

# Compares with the previous list, then replaces it. The baseline is removed
# only when the new list is complete.
manage_diffs() {
    [ "$PKGLIST_OK" = true ] || return 0
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

# Package cleaning runs only after a successful backup, so a failed run never
# changes the system it could not save.
clean_packages() {
    local id_check="${ID_LIKE:-${ID:-}}"
    case "$id_check" in
        *arch*) yay -Sc --noconfirm ;;
        *debian*) sudo apt autoremove --purge -y ;;
    esac
}

# --- Backup function ---
# Concatenates the exclude sources into $1, forcing a newline after each file
# so a source without a trailing newline cannot merge two patterns.
build_excludes() {
    local out="$1"
    local f
    local dist_dir="${DOTFILES_REPOSITORY}/dist"

    if [ -f "${HOME}/.no_backup.txt" ]; then
        cat "${HOME}/.no_backup.txt" >> "$out"
        printf '\n' >> "$out"
    fi
    for f in "$dist_dir"/*_excludes.txt; do
        if [ -f "$f" ]; then
            cat "$f" >> "$out"
            printf '\n' >> "$out"
        fi
    done
}

# A missing or empty source (unmounted, wrong path) would make --delete wipe
# the whole remote copy.
source_is_populated() {
    [ -d "$1" ] && [ -n "$(find "$1" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]
}

# Maps an rsync status to the one the run keeps: 24 (vanished files) is only
# a warning; everything else non-zero is a failure.
rsync_effective_status() {
    local rc="$1"
    case "$rc" in
        0) return 0 ;;
        24)
            log "WARNING: some files vanished during transfer (rsync 24)." "$C_ORANGE" >&2
            return 0
            ;;
        23)
            log "ERROR: rsync could not transfer or read some files (23). rsync skips deletions on I/O errors, so stale files can stay on the remote; run with enough rights or exclude the unreadable paths." "$C_RED" >&2
            return "$rc"
            ;;
        25)
            log "ERROR: rsync stopped at the deletion limit (25); re-run with --force-delete if intended." "$C_RED" >&2
            return "$rc"
            ;;
        *)
            log "ERROR: rsync failed with status ${rc}." "$C_RED" >&2
            return "$rc"
            ;;
    esac
}

# Never aborts the script: returns the effective status of this source.
perform_rsync() {
    local src="$1"
    local subfolder="$2"
    local full_dest_path="${REMOTE_BASE_PATH}/${subfolder}"
    local exclude_tmp plan_tmp rsync_rc=0
    local -a delete_limit=()

    log "--- Syncing $src → ${REMOTE_HOST}:${full_dest_path} ---" "$C_ORANGE"

    if ! source_is_populated "$src"; then
        log "ERROR: Source '$src' is missing or empty; refusing to sync (--delete would wipe the remote copy)." "$C_RED" >&2
        return 1
    fi

    if ! run_ssh "${REMOTE_USER}@${REMOTE_HOST}" \
        "mkdir -p -- $(quote_remote_arg "$full_dest_path")"; then
        log "ERROR: Could not create ${full_dest_path} on the remote." "$C_RED" >&2
        return 1
    fi

    new_temp_file
    exclude_tmp="$NEW_TEMP_PATH"
    new_temp_file
    plan_tmp="$NEW_TEMP_PATH"
    build_excludes "$exclude_tmp"

    PLAN_DELETIONS=0
    if collect_rsync_volumes "$src" "$full_dest_path" "$exclude_tmp" "$plan_tmp"; then
        if [ "$FORCE_DELETE" != true ] && [ "$MAX_DELETIONS" -gt 0 ] \
            && [ "$PLAN_DELETIONS" -gt "$MAX_DELETIONS" ]; then
            log "ERROR: ${PLAN_DELETIONS} deletions planned for ${src} (limit ${MAX_DELETIONS}); skipped. Check the exclusions and the source, then re-run with --force-delete." "$C_RED" >&2
            rm -f "$exclude_tmp" "$plan_tmp"
            return 1
        fi
    else
        VOLUME_STATS_AVAILABLE=false
        log "WARNING: Could not estimate rsync change volumes." "$C_ORANGE" >&2
    fi
    rm -f "$plan_tmp"

    # rsync enforces the same limit itself as a backstop (status 25).
    if [ "$FORCE_DELETE" != true ] && [ "$MAX_DELETIONS" -gt 0 ]; then
        delete_limit=("--max-delete=${MAX_DELETIONS}")
    fi

    rsync --force --archive --xattrs \
        --no-specials --no-devices \
        --delete --delete-excluded \
        "${delete_limit[@]}" \
        -e "$RSYNC_SSH" \
        "${RSYNC_INFO[@]}" \
        --exclude-from="$exclude_tmp" \
        "${src}" "${REMOTE_USER}@${REMOTE_HOST}:${full_dest_path}/" || rsync_rc=$?

    rm -f "$exclude_tmp"
    rsync_effective_status "$rsync_rc"
}

parse_arguments() {
    local argument value
    VERBOSE=false
    CLEAN_PACKAGES=false
    FORCE_DELETE=false
    MAX_DELETIONS="${BACKUP_MAX_DELETIONS:-$DEFAULT_MAX_DELETIONS}"
    for argument in "$@"; do
        case "$argument" in
            -v|--verbose) VERBOSE=true ;;
            --clean-packages) CLEAN_PACKAGES=true ;;
            --force-delete) FORCE_DELETE=true ;;
            --max-deletions=*)
                value="${argument#--max-deletions=}"
                MAX_DELETIONS="$value"
                ;;
            *)
                printf 'Usage: %s [-v|--verbose] [--clean-packages] [--force-delete] [--max-deletions=N]\n' "$0" >&2
                return 2
                ;;
        esac
    done
    if ! [[ "$MAX_DELETIONS" =~ ^[0-9]+$ ]]; then
        printf 'Invalid deletion limit: %s\n' "$MAX_DELETIONS" >&2
        return 2
    fi
}

main() {
    local worst=0 rc start finish size_before size_after delta="" source_spec

    parse_arguments "$@" || exit $?

    # shellcheck source=/etc/os-release
    . "${BACKUP_OS_RELEASE:-/etc/os-release}"

    REMOTE_HOST="pads918.home.lan"
    CURRENT_HOSTNAME="$(hostnamectl hostname)"
    REMOTE_USER="$(id -un)"
    validate_identity || exit 1
    REMOTE_BASE_PATH="/volume1/NetBackup/${CURRENT_HOSTNAME}"

    # Ensure SSH keys are loaded in the agent
    if ! ssh-add -l >/dev/null 2>&1; then
        log "ERROR: No SSH keys loaded in agent." "$C_RED" >&2
        exit 1
    fi

    # SSH ControlMaster reuses a single authenticated connection across all
    # ssh/rsync calls. The socket lives in a private (0700) directory.
    SSH_CONTROL_DIR="$(mktemp -d "${XDG_RUNTIME_DIR:-/tmp}/backup-ssh.XXXXXX")"
    SSH_CONTROL_SOCKET="${SSH_CONTROL_DIR}/control"
    build_rsync_ssh
    trap cleanup EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM

    # Open master connection once
    run_ssh -fN "${REMOTE_USER}@${REMOTE_HOST}"

    DOTFILES_REPOSITORY="${DOTFILES_REPOSITORY:-${HOME}/.dotfiles}"
    TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"

    # Package list paths: the newest existing list is the baseline.
    DIST_DIR="${DOTFILES_REPOSITORY}/dist/${ID}"
    mkdir -p "${DIST_DIR}"
    PKGLIST_OLD=""
    local candidate
    for candidate in "${DIST_DIR}"/pkglist-*.txt; do
        [ -f "$candidate" ] && PKGLIST_OLD="$candidate"
    done
    PKGLIST_CURRENT="${DIST_DIR}/pkglist-${TIMESTAMP}-${ID}.txt"

    if [ "$VERBOSE" = true ]; then
        RSYNC_INFO=("--info=progress2,name1,stats2" --itemize-changes)
    else
        RSYNC_INFO=("--info=progress2,name0,stats2")
    fi

    ADDED_BYTES=0
    DELETED_BYTES=0
    MODIFIED_BYTES=0
    VOLUME_STATS_AVAILABLE=true
    PLAN_DELETIONS=0

    manage_packages
    manage_diffs

    start="$(date +%s)"
    size_before="$(get_remote_size)" || size_before=""

    # Every source runs; the run's status is the worst one.
    for source_spec in "${HOME}/|home/${REMOTE_USER}" "/etc/|etc"; do
        rc=0
        perform_rsync "${source_spec%%|*}" "${source_spec#*|}" || rc=$?
        if [ "$rc" -gt "$worst" ]; then
            worst="$rc"
        fi
    done

    size_after="$(get_remote_size)" || size_after=""
    if [[ "$size_before" =~ ^[0-9]+$ && "$size_after" =~ ^[0-9]+$ ]]; then
        delta="$(format_size $(( size_after - size_before )))"
    fi

    finish="$(date +%s)"
    if [ "$worst" -eq 0 ]; then
        log "Backup completed in $(( (finish - start) / 60 ))m $(( (finish - start) % 60 ))s" "$C_GREEN"
    else
        log "Backup finished with errors (status ${worst}) in $(( (finish - start) / 60 ))m $(( (finish - start) % 60 ))s" "$C_RED" >&2
    fi
    if [ "$VOLUME_STATS_AVAILABLE" = true ]; then
        log "Estimated volume added: $(format_volume "$ADDED_BYTES")" "$C_GREEN"
        log "Estimated volume deleted: $(format_volume "$DELETED_BYTES")" "$C_GREEN"
        log "Estimated volume modified (new file sizes): $(format_volume "$MODIFIED_BYTES")" "$C_GREEN"
    else
        log "Change volume summary unavailable." "$C_ORANGE"
    fi
    if [ -n "$delta" ]; then
        log "Disk space delta: $delta" "$C_GREEN"
    else
        log "Disk space delta unavailable." "$C_ORANGE"
    fi

    if [ "$CLEAN_PACKAGES" = true ]; then
        if [ "$worst" -eq 0 ]; then
            clean_packages || worst=$?
        else
            log "Package cleaning skipped: the backup did not succeed." "$C_ORANGE" >&2
        fi
    fi

    return "$worst"
}

# Sourcing the file (tests) only defines the functions.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi
