#!/bin/sh
# POSIX-compliant backup script
set -eu

# --- Verbose option ---
VERBOSE=false
case "${1:-}" in
    -v|--verbose) VERBOSE=true ;;
esac

# --- Configuration ---
# shellcheck source=/etc/os-release
. /etc/os-release

CURRENT_HOSTNAME="$(hostnamectl hostname)"
REMOTE_HOST="pads918.home.lan"
REMOTE_USER="$(id -un)"
REMOTE_BASE_PATH="/volume1/NetBackup/${CURRENT_HOSTNAME}"

# SSH key selection — fail early if neither key exists
SSH_KEY="${HOME}/.ssh/id_rsa"
if [ ! -f "$SSH_KEY" ]; then
    SSH_KEY="${HOME}/.ssh/id_ed25519"
fi
if [ ! -f "$SSH_KEY" ]; then
    printf '\033[0;31mERROR: No SSH key found.\033[0m\n' >&2
    exit 1
fi

# SSH ControlMaster — reuses a single authenticated connection
# across all ssh/rsync calls, avoiding repeated handshakes.
SSH_CONTROL_SOCKET="/tmp/backup-ssh-${REMOTE_HOST}-$$"

# Wrapper: run ssh with consistent options
run_ssh() {
    ssh -i "$SSH_KEY" \
        -o StrictHostKeyChecking=accept-new \
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

BASEDIR="$(dirname "$(readlink -f "$0")")"
TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"

# Package list paths
DIST_DIR="${BASEDIR}/../dist/${ID}"
mkdir -p "${DIST_DIR}"
PKGLIST_OLD="$(ls -1 "${DIST_DIR}"/pkglist-*.txt 2>/dev/null | tail -1 || true)"
PKGLIST_CURRENT="${DIST_DIR}/pkglist-${TIMESTAMP}-${ID}.txt"

# Rsync SSH command string (no arrays in POSIX sh)
RSYNC_SSH="ssh -i ${SSH_KEY} -o StrictHostKeyChecking=accept-new \
    -o ControlMaster=auto -o ControlPath=${SSH_CONTROL_SOCKET} \
    -o ControlPersist=60"

if [ "$VERBOSE" = true ]; then
    RSYNC_INFO="--info=progress2,name1,stats2 --itemize-changes"
else
    RSYNC_INFO="--info=progress2,name0,stats2"
fi

# --- Colours & logging ---
C_ORANGE='\033[0;33m'
C_GREEN='\033[0;32m'
C_RED='\033[0;31m'
C_NC='\033[0m'

log() { printf "${2:-${C_NC}}%s${C_NC}\n" "$1"; }

# --- OS maintenance ---
manage_packages() {
    local id_check="${ID_LIKE:-$ID}"
    log "Vérification des paquets ($id_check)..." "$C_ORANGE"

    case "$id_check" in
        *arch*)
            # pacman -Qtdq exits 1 when no orphans — suppress with || true
            orphans="$(pacman -Qtdq 2>/dev/null || true)"
            if [ -n "$orphans" ]; then
                log "Suppression des orphelins..." "$C_ORANGE"
                printf '%s\n' "$orphans" | xargs yay -Rns --noconfirm
            fi
            yay -Scc --noconfirm
            pacman -Qqe | awk '{print $1}' > "${PKGLIST_CURRENT}"
            ;;
        *debian*)
            sudo apt autoremove --purge -y
            dpkg --get-selections '*' > "${PKGLIST_CURRENT}"
            ;;
    esac
}

manage_diffs() {
    if [ -n "${PKGLIST_OLD}" ] && [ -s "${PKGLIST_OLD}" ]; then
        local diff_file="${DIST_DIR}/pkglist-${TIMESTAMP}.diff"
        diff -U 0 "${PKGLIST_OLD}" "${PKGLIST_CURRENT}" > "${diff_file}" || true
        if [ -s "${diff_file}" ]; then
            log "Changements paquets :" "$C_ORANGE"
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

    [ -f "${HOME}/.no_backup.txt" ] && cat "${HOME}/.no_backup.txt" >> "$exclude_tmp"
    dotfiles_dist="${HOME}/.dotfiles/dist"
    for f in "$dotfiles_dist"/*_excludes.txt; do
        [ -f "$f" ] && cat "$f" >> "$exclude_tmp"
    done

    # Exit code 23 = some files skipped (e.g. symlinks with --no-links) — not a real error
    # shellcheck disable=SC2086
    rsync --force --archive --perms --xattrs \
        --no-specials --no-devices --no-links \
        --delete --delete-excluded \
        -e "$RSYNC_SSH" \
        $RSYNC_INFO \
        --exclude-from="$exclude_tmp" \
        "${src}" "${REMOTE_USER}@${REMOTE_HOST}:${full_dest_path}/" \
        || { rc=$?; [ "$rc" -eq 23 ] || { rm -f "$exclude_tmp"; exit "$rc"; }; }

    rm -f "$exclude_tmp"
}

# --- Execution ---
if ! ping -c 1 -W 2 "$REMOTE_HOST" > /dev/null 2>&1; then
    log "ERREUR: $REMOTE_HOST injoignable." "$C_RED"
    exit 1
fi

manage_packages
manage_diffs

START="$(date +%s)"

perform_rsync "${HOME}/" "home/${REMOTE_USER}"
perform_rsync "/etc/" "etc"

FINISH="$(date +%s)"
log "Backup terminé en $(( (FINISH - START) / 60 ))m $(( (FINISH - START) % 60 ))s" "$C_GREEN"
