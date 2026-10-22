# General aliases

if command -v tofu &>/dev/null; then
    alias terraform="tofu"
fi

## Medias Sync
_mediasync="${HOME}/.local/bin/mediasync"
[ -x "$_mediasync" ] && alias mediasync="$_mediasync"
unset _mediasync

## Backup
[ -f "${HOME}/.bin/backup.sh" ] && \
  alias backup="${HOME}/.bin/backup.sh"
