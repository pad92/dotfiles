# General aliases

if [ $(command -v tofu) ]; then
    alias terraform="tofu"
fi

## Medias Sync
alias mediasync="${HOME}/Documents/git/git.home.lan/pascal/tools/mediasync.py"

## Backup
[ -f "${HOME}/.dotfiles/bin/backup.sh" ] && \
  alias backup="${HOME}/.dotfiles/bin/backup.sh"
