export LANG=en_US.UTF-8
export EDITOR='vim'
export ELECTRON_TRASH=gio

if [ -n "$DESKTOP_SESSION" ];then
    eval $(gnome-keyring-daemon --start 2>/dev/null)
    export SSH_AUTH_SOCK
fi
