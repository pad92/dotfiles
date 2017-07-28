export ZSH=${HOME}/.dotfiles/zsh/
export TERM="xterm-256color"

export PATH=$PATH:~/.cabal/bin:~/.xmonad/bin

ZSH_THEME="pad"

plugins=(command-not-found  extract  github  httpie  rsync)

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

if [ -f /usr/share/virtualenvwrapper/virtualenvwrapper.sh ]
then
  export WORKON_HOME=${HOME}/.virtualenvs
  export PROJECT_HOME=${HOME}/Devel
  source /usr/share/virtualenvwrapper/virtualenvwrapper.sh
fi
