export ZSH=${HOME}/.dotfiles/zsh/

if [ -d "${HOME}/.bin" ]; then
  export PATH="${PATH}:${HOME}/.bin"
  rehash
fi

if [ -d "${HOME}/.local/bin" ]; then
  export PATH="${PATH}:${HOME}/.local/bin"
  rehash
fi

if [ -d /usr/bin/vendor_perl ]; then
  export PATH="${PATH}:/usr/bin/vendor_perl"
  rehash
fi

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

export ZSH_CACHE_DIR=${HOME}/.zcache
source ${ZSH}/init.zsh

_comp_options+=(globdots)

# User configuration
export LANG="en_US.UTF-8"
export EDITOR='vim'

# History
export HIST_STAMPS="%d/%m/%y %T"
export HISTFILE=${HOME}/.zsh_history
export HISTSIZE=1000000000
export SAVEHIST=$HISTSIZE

setopt BANG_HIST                 # Treat the '!' character specially during expansion.
setopt EXTENDED_HISTORY          # Write the history file in the ":start:elapsed;command" format.
setopt HIST_BEEP                 # Beep when accessing nonexistent history.
setopt HIST_EXPIRE_DUPS_FIRST    # Expire duplicate entries first when trimming history.
setopt HIST_FIND_NO_DUPS         # Do not display a line previously found.
setopt HIST_IGNORE_ALL_DUPS      # Delete old recorded entry if new entry is a duplicate.
setopt HIST_IGNORE_DUPS          # Don't record an entry that was just recorded again.
setopt HIST_IGNORE_SPACE         # Don't record an entry starting with a space.
setopt HIST_REDUCE_BLANKS        # Remove superfluous blanks before recording entry.
setopt HIST_SAVE_NO_DUPS         # Don't write duplicate entries in the history file.
setopt HIST_VERIFY               # Don't execute immediately upon history expansion.
setopt INC_APPEND_HISTORY        # Write to the history file immediately, not when the shell exits.
setopt SHARE_HISTORY             # Share history between all sessions.

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

if uwsm check may-start && uwsm select; then
	exec uwsm start default
fi
