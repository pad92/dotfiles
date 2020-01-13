#!/bin/sh

xrandr | grep -q 'HDMI-\?1-\?1\? connected'
HDMI1="${?}"

xrandr | grep -q 'HDMI-\?2-\?2\? connected'
HDMI2="${?}"

if [ "${HDMI1}" -eq 0 ] && [ "${HDMI2}" -eq 0 ]; then
    # HDMI-2 HDMI-1
    #        eDP-1
    xrandr --output eDP-1 --primary --mode 1920x1080 --pos 1920x1080 --rotate normal \
           --output DP-1 --off \
           --output DP-2 --off \
           --output HDMI-1 --mode 1920x1080 --pos 1920x0 --rotate normal \
           --output HDMI-2 --mode 1920x1080 --pos 0x0 --rotate normal
elif [ "${HDMI1}" -eq 0 ] && [ "${HDMI2}" -eq 1 ]; then
    # HDMI-1 eDP-1
    xrandr --output eDP-1 --primary --mode 1920x1080 --pos 1920x1080 --rotate normal \
           --output DP-1 --off \
           --output DP-2 --off \
           --output HDMI-1 --mode 1920x1080 --pos 1920x0 --rotate normal \
           --output HDMI-2 --off 
else
    # eDP-1
    xrandr --output eDP-1 --primary --mode 1920x1080 --pos 1920x1080 --rotate normal \
           --output DP-1 --off \
           --output DP-2 --off \
           --output HDMI-1 --off \
           --output HDMI-2 --off
fi

feh --randomize --bg-scale ~/Pictures/Wallpapers/*.jpg
