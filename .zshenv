export LANG=en_US.UTF-8
export EDITOR='vim'
export VISUAL='vim'
export PAGER=less
export ELECTRON_TRASH=gio
export TERM="${TERM:-xterm-256color}"

if [[ -o interactive ]]; then
  _gpg_tty="$(tty 2>/dev/null || true)"
  if [[ -n "$_gpg_tty" && "$_gpg_tty" != "not a tty" ]]; then
    export GPG_TTY="$_gpg_tty"
  fi
  unset _gpg_tty
fi

# PIP
export PATH="${HOME}/.local/bin:${PATH}"
