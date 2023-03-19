#!/bin/sh

LISTMONITORS=$(xrandr --current --listmonitors | grep -v '^Monitors' | awk '{print $NF}' | sort | tr '\n' ' ' | sed 's/ $//g')

[ -f /proc/acpi/button/lid/LID0/state ] && LID_STATE=$(grep -oE '[^ ]+$' /proc/acpi/button/lid/LID0/state)

# 	xrandr --setprovideroutputsource modesetting NVIDIA-0

case "${LISTMONITORS}" in
'DP-1-1 DP-1-2')  # anker @ home
  DPI=96
  echo "Xft.dpi: ${DPI}" | xrdb -merge
  xrandr --dpi ${DPI} \
    --output eDP-1  --off \
    --output DP-2-1           --auto --left-of  DP-2-2 \
    --output DP-2-2 --primary --auto
  i3-msg "workspace 1, move workspace to output DP-2-2"
  i3-msg "workspace 2, move workspace to output DP-2-1"
  #pkill xautolock ; xset s off ; xset -dpms ; xset s noblank
  ;;

'DP-3-1 DP-3-8 eDP-1')  # anker @ home
  DPI=96
  echo "Xft.dpi: ${DPI}" | xrdb -merge
  xrandr --dpi ${DPI} \
    --output eDP-1            --auto --below DP-3-8 --scale 0.5x0.5 \
    --output DP-3-8           --auto --left-of  DP-3-1 \
    --output DP-3-1 --primary --auto
  i3-msg "workspace 8, move workspace to output eDP-1"
  i3-msg "workspace 1, move workspace to output DP-3-1"
  i3-msg "workspace 2, move workspace to output DP-3-8"
  #pkill xautolock ; xset s off ; xset -dpms ; xset s noblank
  ;;

'eDP1')                 # alone
  DPI=220
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
