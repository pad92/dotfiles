export ZSH=${HOME}/.dotfiles/zsh/

ZSH_THEME="disaster"

# Uncomment the following line to use case-sensitive completion.
# CASE_SENSITIVE="true"

# Uncomment the following line to disable colors in ls.
# DISABLE_LS_COLORS="true"

# Uncomment the following line to disable auto-setting terminal title.
# DISABLE_AUTO_TITLE="true"

plugins=(command-not-found  extract  github  httpie  rsync  virtualenv  zsh_reload)

# User configuration
export ZSH_CACHE_DIR=~/.zcache

source ${ZSH}/init.zsh

export LANG=en_US.UTF-8
export EDITOR='vim'

if [ -f ${HOME}/.zshaliases ]
then
  source ${HOME}/.zshaliases
fi

export WORKON_HOME=$HOME/.virtualenvs
export PROJECT_HOME=$HOME/Devel
source /usr/share/virtualenvwrapper/virtualenvwrapper.sh


