export ZSH=${HOME}/.dotfiles/zsh/
export TERM=xterm-color


if [ -d ${HOME}/.bin ]; then
    export PATH="${PATH}:${HOME}/.bin"
    for MYBIN in $(ls -d ${HOME}/.bin/*/); do
        if [ -d "${MYBIN}" ]; then
           export PATH="${PATH}:${MYBIN}"
        fi
    done
    rehash
fi

if [ -d ${HOME}/.local/bin ]; then
    export PATH="${PATH}:${HOME}/.local/bin"
fi

ZSH_THEME="pad"

plugins=(
  ansible
  brew
  command-not-found
  docker
  docker-compose
  extract
  github
  httpie
  rsync
)

export ZSH_CACHE_DIR=${HOME}/.zcache
source ${ZSH}/init.zsh

# User configuration
export LANG="en_US.UTF-8"
export LC_COLLATE="en_US.UTF-8"
export LC_CTYPE="en_US.UTF-8"
export LC_MESSAGES="en_US.UTF-8"
export LC_MONETARY="en_US.UTF-8"
export LC_NUMERIC="en_US.UTF-8"
export LC_TIME="en_US.UTF-8"
export LC_ALL="en_US.UTF-8"

export EDITOR='vim'

# History
export HISTCONTROL=$HISTCONTROL${HISTCONTROL+,}ignoredups
export HISTCONTROL=$HISTCONTROL${HISTCONTROL+,}ignorespace
export HISTFILE=${HOME}/.zsh_history
export HISTIGNORE="&:ls:ll:la:l.:pwd:exit:clear:clr:[bf]g"

setopt auto_cd
setopt extended_history
setopt hist_expire_dups_first
setopt hist_ignore_all_dups
setopt hist_verify
setopt inc_append_history
setopt share_history

setopt SHARE_HISTORY
setopt APPEND_HISTORY


if [ -f ${HOME}/.zshaliases ]
then
  source ${HOME}/.zshaliases
fi

if [ -f /usr/bin/neofetch ]; then /usr/bin/neofetch; fi
if [ -f "${HOME}/.dir_colors" ]; then eval $(dircolors ${HOME}/.dir_colors); fi

test -e "${HOME}/.iterm2_shell_integration.zsh" && source "${HOME}/.iterm2_shell_integration.zsh"

