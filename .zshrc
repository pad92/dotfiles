export ZSH=${HOME}/.dotfiles/zsh/
export TERM=xterm-256color

#

if [ -d ${HOME}/.bin ]; then
    export PATH="${PATH}:${HOME}/.bin"
#    for MYBIN in $(ls -d ${HOME}/.bin/*/ 2>/dev/null); do
#        if [ -d "${MYBIN}" ]; then
#            export PATH="${PATH}:${MYBIN}"
#        fi
#    done
    rehash
fi

if [ -d ${HOME}/.local/bin ]; then
    export PATH="${PATH}:${HOME}/.local/bin"
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

if [[ "${OSTYPE}" =~ ^darwin.*$ ]]; then
    plugins=(${plugins}
        brew)
fi

export ZSH_CACHE_DIR=${HOME}/.zcache
source ${ZSH}/init.zsh

# User configuration
export LANG="en_US.UTF-8"
export EDITOR='vim'

if [[ -e /usr/share/zsh/manjaro-zsh-config ]]; then
    source /usr/share/zsh/manjaro-zsh-config
fi
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


if [ -f ${HOME}/.zshaliases ]
then
  source ${HOME}/.zshaliases
fi

if [ -f "${HOME}/.dir_colors" ]; then eval $(dircolors ${HOME}/.dir_colors); fi

if [[ "${OSTYPE}" =~ ^darwin.*$ ]]; then
    test -e "${HOME}/.iterm2_shell_integration.zsh" && source "${HOME}/.iterm2_shell_integration.zsh"
else
    STARTX_BIN=$(command -v startx )
    if [ ! -z "${STARTX_BIN}" ] ; then
        [[ $(tty) == '/dev/tty1' ]] && startx
    fi
fi

if [ -x $(command -v neofetch) ]; then neofetch; fi

USE_POWERLINE="true"

if [[ -e /usr/share/zsh/manjaro-zsh-prompt ]]; then
    source /usr/share/zsh/manjaro-zsh-prompt
fi
