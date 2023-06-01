#!/bin/sh
. /etc/os-release

BACKUP_DIR="pascal@192.168.0.100:backup"
HOSTNAME="$(hostnamectl hostname)"

BASEDIR=$(dirname "$0")
TIMESTAMP=$(date "+%Y%m%d-%H%M%S")
RSYNC_OPTS='--archive --perms --xattrs --safe-links --no-specials --no-devices --info=progress2 --delete --delete-excluded'
SUDO_OPTS='-E -s'
#if [ ! -d "${BACKUP_DIR}/${HOSTNAME}${HOME}/" ]; then
#  echo "create ${BACKUP_DIR}/${HOSTNAME}${HOME}/"
#  sudo mkdir -p "${BACKUP_DIR}/${HOSTNAME}${HOME}/"
#fi
PKGLIST_OLD="$(ls -1 ${BASEDIR}/../dist/${ID}/pkglist-*.txt 2>/dev/null | tail -1)"
PKGLIST_CURRENT="${BASEDIR}/../dist/${ID}/pkglist-${TIMESTAMP}-${ID}.txt"

[ -z "${ID_LIKE}" ] && ID_LIKE="${ID}"

case $ID_LIKE in
arch)
  ORPHAN=$(pacman -Qtdq)

  if [ -n "${ORPHAN}" ]; then
    echo "Remove orphans"
    yay -Rs $(pacman -Qtdq)
  fi

  yay -Scc --noconfirm

  pacman -Qqe | awk '{print $1}' | tee -a ${PKGLIST_CURRENT} 1>/dev/null

  ;;
debian)
  sudo apt autoremove --purge
  dpkg --get-selections '*' | tee -a ${PKGLIST_CURRENT} 1>/dev/null

  ;;

*)
  echo "unknown"
  exit 1
  ;;
esac

if [ -s "${PKGLIST_OLD}" ]; then
  diff -U 0 "${PKGLIST_OLD}" "${PKGLIST_CURRENT}" > "${BASEDIR}/../dist/${ID}/pkglist-${TIMESTAMP}.diff"
  if [ -s "${BASEDIR}/../dist/${ID}/pkglist-${TIMESTAMP}.diff" ]; then
    cat "${BASEDIR}/../dist/${ID}/pkglist-${TIMESTAMP}.diff"
  else
    rm -f "${BASEDIR}/../dist/${ID}/pkglist-${TIMESTAMP}.diff"
  fi
fi

sudo ${SUDO_OPTS} rsync ${RSYNC_OPTS} ${HOME}/ ${BACKUP_DIR}/${HOSTNAME}${HOME}/ --delete-excluded --exclude-from=- <<- EOF
$(cat ${HOME}/.no_backup.txt ${HOME}/.dotfiles/dist/*_excludes.txt)
EOF
