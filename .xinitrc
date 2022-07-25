#!/bin/sh

userresources=$HOME/.Xresources
XMODMAP_USER=$HOME/.Xmodmap
XRESOURCES_ETC=/etc/X11/xinit/.Xresources
XMODPAM_ETC=/etc/X11/xinit/.Xmodmap

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

xrandr --setprovideroutputsource modesetting NVIDIA-0
xrandr --auto
exec ~/.screenlayout/modseting-nvidia.sh
exec nitrogen --restore
exec i3 >> ~/.cache/i3.log 2>> ~/.cache/i3.err
