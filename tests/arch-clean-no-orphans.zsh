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

# yay may exit without reading its answer. A writer process piped into it can
# then die of SIGPIPE, which pipefail reports as a failed cache cleanup. A
# delayed echo makes that ordering certain instead of rare.
echo() { sleep 0.2; builtin echo "$@"; }
clean_arch >/dev/null
unfunction echo
print 'PASS: clean_arch does not fail when yay ignores its input'

# yay -Scc defaults to keeping the cache, so it must still be answered "y".
yay() { local answer; read -r answer && [[ $answer == y ]]; }
clean_arch >/dev/null
print 'PASS: clean_arch answers yes to the yay cache prompt'
yay() { return 0; }

pacman() {
  print -u2 'error: package database unavailable'
  return 1
}
if clean_arch >/dev/null 2>&1; then
  print -u2 'FAIL: clean_arch ignored a package database error'
  exit 1
fi
print 'PASS: clean_arch reports package database errors'
