#!/bin/sh

xrandr | grep -q 'HDMI-\?1-\?1\? connected'
HDMI1="${?}"

xrandr | grep -q 'HDMI-\?2-\?2\? connected'
HDMI2="${?}"

if [ "${HDMI1}" -eq 0 ] && [ "${HDMI2}" -eq 0 ]; then
    # HDMI-2 HDMI-1
    #        eDP-1
    xrandr --dpi 96 --output eDP-1 --primary --mode 1920x1080 --output HDMI-1 --auto --above eDP-1 --output HDMI-2 --auto --left-of HDMI-1 
elif [ "${HDMI1}" -eq 0 ] && [ "${HDMI2}" -eq 1 ]; then
    # HDMI-1 eDP-1
    xrandr --dpi 96 --output eDP-1 --primary --mode 1920x1080 --output HDMI-1 --auto --left-of eDP-1
else
    # eDP-1
    xrandr --dpi 96 --output eDP-1 --primary --mode 1920x1080
fi

feh --randomize --bg-scale ~/Pictures/Wallpapers/*.jpg
