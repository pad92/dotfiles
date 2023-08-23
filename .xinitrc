#!/bin/sh

userresources=$HOME/.Xresources
XMODMAP_USER=$HOME/.Xmodmap
XRESOURCES_ETC=/etc/X11/xinit/.Xresources
XMODPAM_ETC=/etc/X11/xinit/.Xmodmap
XRANDR_CMD=/usr/bin/autorandr

# merge in defaults and keymaps
if [ -f $XRESOURCES_ETC ]; then
    xrdb -merge $XRESOURCES_ETC
fi

if [ -f $XMODPAM_ETC ]; then
    xmodmap $XMODPAM_ETC
fi

if [ -f "$userresources" ]; then
    xrdb -merge "$userresources"
fi

if [ -f "$XMODMAP_USER" ]; then
    xmodmap "$XMODMAP_USER"
fi

# start some nice programs
if [ -d /etc/X11/xinit/xinitrc.d ] ; then
 for f in /etc/X11/xinit/xinitrc.d/?*.sh ; do
  [ -x "$f" ] && . "$f"
 done
 unset f
fi

[ -f ~/.xprofile ] && . ~/.xprofile

if [ -x "$XRANDR_CMD" ]; then
    "${XRANDR_CMD}"
else
    xrandr --auto
fi

numlockx &
eval "$(/usr/bin/gnome-keyring-daemon --start --components=pkcs11,secrets,ssh)"
export SSH_AUTH_SOCK
exec dbus-launch --exit-with-session i3
