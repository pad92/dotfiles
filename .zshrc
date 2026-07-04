export ZSH=${HOME}/.dotfiles/zsh/

if [ -d "${HOME}/.bin" ]; then
  export PATH="${PATH}:${HOME}/.bin"
fi

if [ -d "${HOME}/.local/bin" ]; then
  export PATH="${PATH}:${HOME}/.local/bin"
fi

if [ -d /usr/bin/vendor_perl ]; then
  export PATH="${PATH}:/usr/bin/vendor_perl"
fi

rehash

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

autoload -Uz colors && colors
autoload -Uz bashcompinit && bashcompinit

zstyle ':completion:*' menu select
zmodload zsh/complist

# History
# Must be exported before `init.zsh` sources init/history.zsh: the HIST_STAMPS
# case statement there builds the `history` alias at source time, and
# HISTFILE/HISTSIZE/SAVEHIST there only apply a default via ${VAR:-default}.
export HIST_STAMPS="%d/%m/%y %T"
export HISTFILE=${HOME}/.zsh_history
export HISTSIZE=1000000000
export SAVEHIST=$HISTSIZE

setopt HIST_BEEP                 # Beep when accessing nonexistent history.
setopt HIST_IGNORE_SPACE         # Don't record an entry starting with a space.
setopt HIST_VERIFY               # Don't execute immediately upon history expansion.

export ZSH_CACHE_DIR=${HOME}/.zcache
source ${ZSH}/init.zsh

_comp_options+=(globdots)

# User configuration
export LANG="en_US.UTF-8"
export EDITOR='vim'

setopt auto_cd

if [ -d /etc/profile.d ]; then
  if  [ "$(ls -A /etc/profile.d)" ]; then
    for PROFILE_FILE in /etc/profile.d/*.sh; do
      if [ -r "$PROFILE_FILE" ]; then
        . "$PROFILE_FILE"
      fi
    done
  fi
  unset PROFILE_FILE
fi

[ -f "${HOME}/.config/user-dirs.dirs" ] && source ${HOME}/.config/user-dirs.dirs
[ -f "${HOME}/.dir_colors" ]            && eval "$(dircolors "${HOME}/.dir_colors")"
command -v fastfetch >/dev/null 2>&1    && fastfetch

if command -v uwsm >/dev/null 2>&1 && uwsm check may-start && uwsm select; then
  exec uwsm start default
fi
