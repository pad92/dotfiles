export LANG=en_US.UTF-8
export EDITOR='vim'
export VISUAL='vim'
export PAGER=less
export TERMINAL=alacritty
export ELECTRON_TRASH=gio
export TERM="xterm-256color"
export GPG_TTY=$(tty)


# PIP
export PATH="${HOME}/.local/bin:${PATH}"

if [ -n "${DESKTOP_SESSION}" ];then
    eval $(gnome-keyring-daemon --start --components=pkcs11,secrets,ssh 2>/dev/null)
    export SSH_AUTH_SOCK
fi
