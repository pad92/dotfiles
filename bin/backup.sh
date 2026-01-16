#!/bin/bash
set -euo pipefail

# --- Gestion de l'option Verbose ---
VERBOSE=false
if [[ "${1:-}" == "-v" || "${1:-}" == "--verbose" ]]; then
    VERBOSE=true
fi

# --- Configuration ---
source /etc/os-release

CURRENT_HOSTNAME="$(hostnamectl hostname)"
REMOTE_HOST="pads918.home.lan"
REMOTE_USER="$(whoami)"
REMOTE_BASE_PATH="/volume1/NetBackup/PadsTower/home/pascal/${CURRENT_HOSTNAME}"

SSH_KEY="${HOME}/.ssh/id_rsa"
[ ! -f "$SSH_KEY" ] && SSH_KEY="${HOME}/.ssh/id_ed25519"

BASEDIR=$(dirname "$(readlink -f "$0")")
TIMESTAMP=$(date "+%Y%m%d-%H%M%S")

# Chemins des listes de paquets
DIST_DIR="${BASEDIR}/../dist/${ID}"
mkdir -p "${DIST_DIR}"
PKGLIST_OLD="$(ls -1 "${DIST_DIR}"/pkglist-*.txt 2> /dev/null | tail -1 || true)"
PKGLIST_CURRENT="${DIST_DIR}/pkglist-${TIMESTAMP}-${ID}.txt"

# --- Options Rsync Dynamiques ---
RSYNC_OPTS=(
    --force --archive --perms --xattrs --safe-links
    --no-specials --no-devices --no-links
    --delete --delete-excluded
    -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new"
)

if [ "$VERBOSE" = true ]; then
    # Mode détaillé : affiche les fichiers modifiés et leurs détails (taille, date, etc.)
    RSYNC_OPTS+=(--info=progress2,name1,stats2 --itemize-changes)
else
    # Mode discret : affiche seulement la progression globale
    RSYNC_OPTS+=(--info=progress2,name0,stats2)
fi

# Couleurs
C_ORANGE='\033[0;33m'
C_GREEN='\033[0;32m'
C_RED='\033[0;31m'
C_NC='\033[0m'

log() { printf "${2:-$C_NC}${1}${C_NC}\n"; }

# --- Maintenance OS ---
manage_packages() {
    local id_check="${ID_LIKE:-$ID}"
    log "Vérification des paquets ($id_check)..." "$C_ORANGE"
    case "$id_check" in
        *arch*)
            orphans=$(pacman -Qtdq) || true
            if [ -n "$orphans" ]; then
                log "Suppression des orphelins..." "$C_ORANGE"
                yay -Rns $orphans --noconfirm
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
        [ -s "${diff_file}" ] && { log "Changements paquets :" "$C_ORANGE"; cat "${diff_file}"; } || rm -f "${diff_file}"
        rm -f "${PKGLIST_OLD}"
    fi
}

# --- Fonction de Backup ---
perform_rsync() {
    local src="$1"
    local subfolder="$2"
    local full_dest_path="${REMOTE_BASE_PATH}/${subfolder}"

    log "--- Syncing $src to ${REMOTE_HOST}:${full_dest_path} ---" "$C_ORANGE"

    # Création du dossier distant
    ssh -i "$SSH_KEY" "${REMOTE_USER}@${REMOTE_HOST}" "mkdir -p \"${full_dest_path}\""

    # Compilation des exclusions
    {
        [ -f "${HOME}/.no_backup.txt" ] && cat "${HOME}/.no_backup.txt"
        ls ${HOME}/.dotfiles/dist/*_excludes.txt 2>/dev/null | xargs cat 2>/dev/null || true
    } | sudo rsync "${RSYNC_OPTS[@]}" \
        --exclude-from=- \
        "${src}" "${REMOTE_USER}@${REMOTE_HOST}:${full_dest_path}/"
}

# --- Exécution ---

if ! ping -c 1 -W 2 "$REMOTE_HOST" > /dev/null; then
    log "ERREUR: $REMOTE_HOST injoignable." "$C_RED"
    exit 1
fi

manage_packages
manage_diffs

START=$(date +%s)

perform_rsync "${HOME}/" "home"
perform_rsync "/etc/" "etc"

FINISH=$(date +%s)
log "Backup terminé en $(((FINISH - START) / 60))m $(((FINISH - START) % 60))s" "$C_GREEN"
