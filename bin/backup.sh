#!/bin/sh
. /etc/os-release

BACKUP_DIR="/mnt/pads918/backups"
HOSTNAME="$(hostnamectl hostname)"

BASEDIR=$(dirname "$0")
TIMESTAMP=$(date "+%Y%m%d-%H%M%S")
RSYNC_OPTS='--force --archive --perms --xattrs --safe-links --no-specials --no-devices --no-links --delete --delete-excluded --info=progress2,name0,stats2'
SUDO_OPTS='-s'
#if [ ! -d "${BACKUP_DIR}/${HOSTNAME}${HOME}/" ]; then
#  echo "create ${BACKUP_DIR}/${HOSTNAME}${HOME}/"
#  sudo mkdir -p "${BACKUP_DIR}/${HOSTNAME}${HOME}/"
#fi
PKGLIST_OLD="$(ls -1 ${BASEDIR}/../dist/${ID}/pkglist-*.txt 2> /dev/null | tail -1)"
PKGLIST_CURRENT="${BASEDIR}/../dist/${ID}/pkglist-${TIMESTAMP}-${ID}.txt"

C_ORANGE='\033[0;33m'
C_GREEN='\033[0;32m'
C_NC='\033[0m' # No Color

[ -z "${ID_LIKE}" ] && ID_LIKE="${ID}"

case $ID_LIKE in
  arch)
    ORPHAN=$(pacman -Qtdq)

    if [ -n "${ORPHAN}" ]; then
      echo "Remove orphans"
      yay -Rs $(pacman -Qtdq)
    fi

    yay -Scc --noconfirm

    pacman -Qqe | awk '{print $1}' | tee -a ${PKGLIST_CURRENT} 1> /dev/null

    ;;
  debian)
    sudo apt autoremove --purge
    dpkg --get-selections '*' | tee -a ${PKGLIST_CURRENT} 1> /dev/null

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
  rm -f "${PKGLIST_OLD}"
fi

START=$(date +%s)

[ ! -f "${HOME}/.no_backup.txt" ] && touch "${HOME}/.no_backup.txt"

printf "${C_ORANGE}Syncing ~/ to ${BACKUP_DIR}/${HOSTNAME}${HOME}${C_NC}\n"
sudo ${SUDO_OPTS} rsync ${RSYNC_OPTS} ${HOME}/ ${BACKUP_DIR}/${HOSTNAME}${HOME}/ --delete-excluded --exclude-from=- <<- EOF
$(cat ${HOME}/.no_backup.txt ${HOME}/.dotfiles/dist/*_excludes.txt)
EOF

printf "${C_ORANGE}Syncing /etc to ${BACKUP_DIR}/${HOSTNAME}/etc${C_NC}\n"
sudo ${SUDO_OPTS} rsync ${RSYNC_OPTS} /etc/ ${BACKUP_DIR}/${HOSTNAME}/etc/ --delete-excluded --exclude-from=- <<- EOF
$(cat ${HOME}/.no_backup.txt ${HOME}/.dotfiles/dist/*_excludes.txt)
EOF

FINISH=$(date +%s)
printf "${C_GREEN}rsync total time: $((($FINISH - $START) / 60)) minutes, $((($FINISH - $START) % 60)) seconds${C_NC}\n"
