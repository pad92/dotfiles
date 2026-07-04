# General aliases

if command -v tofu &>/dev/null; then
    alias terraform="tofu"
fi

## Medias Sync
_mediasync="${HOME}/Documents/git/git.home.lan/pascal/tools/mediasync.py"
[ -x "$_mediasync" ] && alias mediasync="$_mediasync"
unset _mediasync

## Backup
[ -f "${HOME}/.dotfiles/bin/backup.sh" ] && \
  alias backup="${HOME}/.dotfiles/bin/backup.sh"
