#!/bin/sh
. /etc/os-release

MNT_PTS='/mnt/pads918/home'
BACKUP_DIR="${MNT_PTS}/${USERNAME}/backup"
HOSTNAME="$(hostnamectl hostname)"

TIMESTAMP=$(date "+%Y%m%d-%H%M%S")
RSYNC_OPTS='--archive --perms --xattrs --safe-links --no-specials --no-devices --info=progress2 --delete --delete-excluded'
SUDO_OPTS='-E -s'
if [ ! -d "${BACKUP_DIR}/${HOSTNAME}${HOME}/" ]; then
  echo "create ${BACKUP_DIR}/${HOSTNAME}${HOME}/"
  sudo mkdir -p "${BACKUP_DIR}/${HOSTNAME}${HOME}/"
fi
PKGLIST_OLD="$(sudo ls -1 ${BACKUP_DIR}/${HOSTNAME}/pkglist-*.txt 2>/dev/null | tail -1)"
PKGLIST_CURRENT="${BACKUP_DIR}/${HOSTNAME}/pkglist-${TIMESTAMP}-${ID}.txt"

[ -z "${ID_LIKE}" ] && ID_LIKE="${ID}"

case $ID_LIKE in
arch)
  ORPHAN=$(pacman -Qtdq)

  if [ -n "${ORPHAN}" ]; then
    echo "Remove orphans"
    yay -Rs $(pacman -Qtdq)
  fi

  yay -Scc --noconfirm

  pacman -Qqe | awk '{print $1}' | sudo tee -a ${PKGLIST_CURRENT} 1>/dev/null

  ;;
debian)
  sudo apt autoremove --purge
  dpkg --get-selections '*' | sudo tee -a ${PKGLIST_CURRENT} 1>/dev/null

  ;;

*)
  echo "unknown"
  exit 1
  ;;
esac

if [ -s "${PKGLIST_OLD}" ]; then
  diff -U 0 "${PKGLIST_OLD}" "${PKGLIST_CURRENT}" > "${BACKUP_DIR}/${HOSTNAME}/pkglist-${TIMESTAMP}.diff"
  if [ -s "${BACKUP_DIR}/${HOSTNAME}/pkglist-${TIMESTAMP}.diff" ]; then
    cat "${BACKUP_DIR}/${HOSTNAME}/pkglist-${TIMESTAMP}.diff"
  else
    rm -f "${BACKUP_DIR}/${HOSTNAME}/pkglist-${TIMESTAMP}.diff"
  fi
fi

sudo rsync ${RSYNC_OPTS} ${HOME}/ ${BACKUP_DIR}/${HOSTNAME}${HOME}/ --exclude-from=- <<- EOF
$(cat ${HOME}/.no_backup.txt ${HOME}/.dotfiles/dist/backup_excludes.txt)
EOF
