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

plugins=(ansible
archlinux
command-not-found
docker
docker-compose
extract
github
httpie
rsync
ssh-agent)

export ZSH_CACHE_DIR=${HOME}/.zcache
source ${ZSH}/init.zsh

# User configuration
export LANG=en_US.UTF-8
export EDITOR='vim'

# History
export HISTCONTROL=erasedups  # Ignore duplicate entries in history
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
if [ -f ${HOME}/.zshenv ]
then
  source ${HOME}/.zshenv
fi

if [ -f /usr/bin/screenfetch ]; then screenfetch; fi
if [ -f "${HOME}/.dir_colors" ]; then eval $(dircolors ${HOME}/.dir_colors); fi
