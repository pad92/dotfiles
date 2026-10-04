ZSH="${HOME}/.dotfiles/zsh"

ZSH_THEME="pad"

plugins=(
  pass-cli
  ansible
  archlinux           # https://github.com/ohmyzsh/ohmyzsh/blob/master/plugins/archlinux/README.md
  docker
  docker-compose
  extract
  github
  httpie
  rsync
  thefuck
  vscode
  zsh-autosuggestions
  zsh-completions
  zsh-syntax-highlighting
)

# History
# Must be set before `init.zsh` sources init/history.zsh: the HIST_STAMPS case
# statement there builds the `history` alias at source time, and
# HISTFILE/HISTSIZE/SAVEHIST there only apply a default via ${VAR:-default}.
HIST_STAMPS="%d/%m/%y %T"
HISTFILE="${HOME}/.zsh_history"
HISTSIZE=100000
SAVEHIST=${HISTSIZE}

setopt HIST_BEEP                 # Beep when accessing nonexistent history.
setopt HIST_IGNORE_SPACE         # Don't record an entry starting with a space.
setopt HIST_VERIFY               # Don't execute immediately upon history expansion.

ZSH_CACHE_DIR="${HOME}/.zcache"
source "${ZSH}/init.zsh"

_comp_options+=(globdots)

[ -f "${HOME}/.config/user-dirs.dirs" ] && source "${HOME}/.config/user-dirs.dirs"
[ -f "${HOME}/.dir_colors" ]            && eval "$(dircolors "${HOME}/.dir_colors")"
if [[ -t 1 && ${SHLVL:-1} -eq 1 ]] && command -v fastfetch >/dev/null 2>&1; then
  fastfetch
fi
