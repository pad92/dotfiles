export ZSH=${HOME}/.dotfiles/zsh/
export TERM="xterm-256color"

ZSH_THEME="disaster"

# Uncomment the following line to use case-sensitive completion.
# CASE_SENSITIVE="true"

# Uncomment the following line to disable colors in ls.
# DISABLE_LS_COLORS="true"

plugins=(command-not-found  extract  github  httpie  rsync)

export ZSH_CACHE_DIR=${HOME}/.zcache
source ${ZSH}/init.zsh

# User configuration
export LANG=en_US.UTF-8
export EDITOR='vim'

if [ -f ${HOME}/.zshaliases ]
then
  source ${HOME}/.zshaliases
fi

if [ -f /usr/share/virtualenvwrapper/virtualenvwrapper.sh ]
then
  export WORKON_HOME=$HOME/.virtualenvs
  export PROJECT_HOME=$HOME/Devel
  source /usr/share/virtualenvwrapper/virtualenvwrapper.sh
fi
