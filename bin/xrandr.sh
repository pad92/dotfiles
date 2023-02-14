#!/bin/sh

LISTMONITORS=$(xrandr --current --listmonitors | grep -v '^Monitors' | awk '{print $NF}' | sort | tr '\n' ' ' | sed 's/ $//g')

[ -f /proc/acpi/button/lid/LID0/state ] && LID_STATE=$(grep -oE '[^ ]+$' /proc/acpi/button/lid/LID0/state)

# 	xrandr --setprovideroutputsource modesetting NVIDIA-0

case "${LISTMONITORS}" in
'DP-1-1 DP-1-2')  # anker @ home
  xrandr --dpi 96 \
    --output eDP-1  --off \
    --output DP-2-1           --auto --left-of  DP-2-2 --rotate right \
    --output DP-2-2 --primary --auto                   --rotate normal
  i3-msg "workspace 1, move workspace to output DP-2-2"
  i3-msg "workspace 2, move workspace to output DP-2-1"
  #pkill xautolock ; xset s off ; xset -dpms ; xset s noblank
  ;;

'DP-2-1 DP-2-2 eDP-1')  # anker @ home
  xrandr --dpi 96 \
    --output eDP-1            --auto --right-of DP-2-2 --rotate normal --scale 0.5x0.5 \
    --output DP-2-1           --auto --left-of  DP-2-2 --rotate right \
    --output DP-2-2 --primary --auto                   --rotate normal
  i3-msg "workspace 0, move workspace to output eDP-1"
  i3-msg "workspace 1, move workspace to output DP-2-2"
  i3-msg "workspace 2, move workspace to output DP-2-1"
  #pkill xautolock ; xset s off ; xset -dpms ; xset s noblank
  ;;

'eDP1')                 # alone
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
