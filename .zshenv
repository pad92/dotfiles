export LANG=en_US.UTF-8
export EDITOR='vim'
export VISUAL='vim'
export PAGER=less
export ELECTRON_TRASH=gio
export TERM="${TERM:-xterm-256color}"

# Keep command lookup deterministic across login, interactive, and nested shells.
# Add the least-preferred directory first because each existing directory is
# prepended; the unique path array removes inherited duplicates.
typeset -gU path PATH
for _path_dir in \
  /usr/bin/vendor_perl \
  /sbin \
  /usr/sbin \
  /usr/local/sbin \
  "${HOME}/local/bin" \
  "${HOME}/.dotfiles/bin" \
  "${HOME}/.local/bin" \
  "${HOME}/.bin"
do
  if [[ -d "${_path_dir}" ]]; then
    path=("${_path_dir}" "${path[@]}")
  fi
done
unset _path_dir
export PATH

if [[ -o interactive ]]; then
  _gpg_tty="$(tty 2>/dev/null || true)"
  if [[ -n "$_gpg_tty" && "$_gpg_tty" != "not a tty" ]]; then
    export GPG_TTY="$_gpg_tty"
  fi
  unset _gpg_tty
fi
