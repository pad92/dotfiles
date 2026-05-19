# General aliases

if [ $(command -v tofu) ]; then
    alias terraform="tofu"
fi

## Medias Sync
alias mediasync="${HOME}/Documents/git/git.home.lan/pascal/tools/mediasync.py"

## Backup
[ -f "${HOME}/.dotfiles/bin/backup.sh" ] && \
  alias backup="${HOME}/.dotfiles/bin/backup.sh"

## System & Utilities
alias volmute="ManageSound.sh mute"
alias volinc="ManageSound.sh inc"
alias voldec="ManageSound.sh dec"
alias volswitch="ManageSound.sh sw"

## Gaming
alias steam-opt="steam-optimize"

## Git
alias ggc="git-gen-commit"

