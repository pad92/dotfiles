export ZSH=${HOME}/.dotfiles/zsh/
export TERM=xterm-256color

if [ -d ${HOME}/.bin ]; then
  export PATH="${PATH}:${HOME}/.bin"
  rehash
fi

if [ -d ${HOME}/.local/bin ]; then
  export PATH="${PATH}:${HOME}/.local/bin"
  rehash
fi

ZSH_THEME="pad"

plugins=(
  ansible
  archlinux           # https://github.com/ohmyzsh/ohmyzsh/blob/master/plugins/archlinux/README.md
  command-not-found
  docker
  docker-compose
  extract
  github
  httpie
  rsync
  docker
  docker-compose
  zsh-autosuggestions
  zsh-completions
  zsh-syntax-highlighting
  thefuck
)

autoload -Uz colors && colors
autoload -Uz compinit && compinit
zstyle ':completion:*' menu select
zmodload zsh/complist
compinit
_comp_options+=(globdots) # incude dotfiles

export ZSH_CACHE_DIR=${HOME}/.zcache
source ${ZSH}/init.zsh

# User configuration
export LANG="en_US.UTF-8"
export EDITOR='vim'

# History
export HIST_STAMPS="mm/dd/yyyy"
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

[ -f "${HOME}/.config/user-dirs.dirs" ] && source ${HOME}/.config/user-dirs.dirs
[ -f "${HOME}/.zshaliases" ]            && source ${HOME}/.zshaliases
[ -f "${HOME}/.dir_colors" ]            && eval $(dircolors ${HOME}/.dir_colors)
[ -x $(command -v neofetch) ]           && neofetch
