#!/bin/sh
. /etc/os-release

MNT_PTS='/mnt/pads918/home'
BACKUP_DIR="pascal@192.168.0.100:backup"
HOSTNAME="$(hostnamectl hostname)"

TIMESTAMP=$(date "+%Y%m%d-%H%M%S")
RSYNC_OPTS='--dry-run --archive --perms --xattrs --safe-links --no-specials --no-devices --info=progress2 --delete'
SUDO_OPTS='-E -s'
echo 'rsync /boot'
sudo ${SUDO_OPTS} rsync ${RSYNC_OPTS} /boot/ ${BACKUP_DIR}/${HOSTNAME}/boot/
echo 'rsync /etc'
sudo ${SUDO_OPTS} rsync ${RSYNC_OPTS} /etc/ ${BACKUP_DIR}/${HOSTNAME}/etc/
echo "rsync ${HOME}"

sudo ${SUDO_OPTS} rsync ${RSYNC_OPTS} --delete-excluded --exclude='Download/' --exclude='Cache/' --exclude-from=${HOME}/.dotfiles/dist/backup_excludes.txt ${HOME}/ "${BACKUP_DIR}/${HOSTNAME}${HOME}/"
