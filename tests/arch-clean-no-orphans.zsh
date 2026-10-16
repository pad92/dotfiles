#!/usr/bin/env zsh

set -euo pipefail
ROOT_DIR=${0:A:h:h}
source "$ROOT_DIR/ansible/roles/dotfiles/files/home/zsh/functions/arch.zsh"

pacman() { return 1; }
yay() { return 0; }
paccache() { return 0; }
sudo() { return 0; }

clean_arch
print 'PASS: clean_arch treats an empty orphan list as success'

pacman() {
  print -u2 'error: package database unavailable'
  return 1
}
if clean_arch >/dev/null 2>&1; then
  print -u2 'FAIL: clean_arch ignored a package database error'
  exit 1
fi
print 'PASS: clean_arch reports package database errors'
