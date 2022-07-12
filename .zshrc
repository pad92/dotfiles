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
export HIST_STAMPS="%d/%m/%y %T"
export HISTCONTROL=$HISTCONTROL${HISTCONTROL+,}ignoredups
export HISTCONTROL=$HISTCONTROL${HISTCONTROL+,}ignorespace
export HISTFILE=${HOME}/.zsh_history
export HISTIGNORE="&:ls:ll:la:l.:pwd:exit:clear:clr:[bf]g"
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

[ -f "${HOME}/.config/user-dirs.dirs" ] && source ${HOME}/.config/user-dirs.dirs
[ -f "${HOME}/.zshaliases" ]            && source ${HOME}/.zshaliases
[ -f "${HOME}/.dir_colors" ]            && eval $(dircolors ${HOME}/.dir_colors)
[ -x $(command -v neofetch) ]           && neofetch
