#!/bin/sh

LISTMONITORS=$(xrandr --current --listmonitors | grep -v '^Monitors' | awk '{print $NF}' | sort | tr '\n' ' ' | sed 's/ $//g')

[ -f /proc/acpi/button/lid/LID0/state ] && LID_STATE=$(grep -oE '[^ ]+$' /proc/acpi/button/lid/LID0/state)

# 	xrandr --setprovideroutputsource modesetting NVIDIA-0

case "${LISTMONITORS}" in
'DP-3 HDMI-1')
  xrandr --dpi 96 \
    --output HDMI-1 --auto --pos 0x0 --rotate right \
    --output DP-3 --primary --auto --pos 1080x0 --rotate normal
  i3-msg "workspace 1, move workspace to output DP-3"
  i3-msg "workspace 2, move workspace to output HDMI-1"
  pkill xautolock
  ;;
'DP1-1 DP3 eDP1')
  #xrandr --setprovideroutputsource modesetting NVIDIA-0
 # xrandr --dpi 96 \
 #   --output eDP1 --auto --scale .5x.5 \
 #   --output DP3 --primary --auto --left-of eDP1 \
 #   --output DP1-1 --auto --left-of DP3 --rotate right
  xrandr --dpi 96 \
    --output eDP1 --off \
    --output DP3 --primary --auto  \
    --output DP1-1 - -auto --left-of DP3 --rotate right
  i3-msg "workspace 1, move workspace to output DP3"
  i3-msg "workspace 2, move workspace to output DP1-1"
  #i3-msg "workspace 3, move workspace to output eDP1"
  pkill xautolock ; xset s off ; xset -dpms ; xset s noblank
  ;;
'DP-1 DP-3-1 eDP-1')
  xrandr --dpi 96 \
    --output eDP-1 --off \
    --output DP-1 --primary --auto \
    --output DP-3-1 --auto --left-of DP-1 --rotate right
  i3-msg "workspace 1, move workspace to output DP-1"
  i3-msg "workspace 2, move workspace to output DP-3-1"
  pkill xautolock ; xset s off ; xset -dpms ; xset s noblank
  ;;
'eDP1')
  DPI=144
  echo "Xft.dpi: ${DPI}" | xrdb -merge
  xrandr --dpi ${DPI}
  ;;
*)
  echo ${LISTMONITORS}
  ;;
esac

if [ $# -eq 1 ]; then
  i3-msg $1
fi

nitrogen --restore
