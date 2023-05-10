#!/bin/sh

LISTMONITORS=$(xrandr| grep -E '^DP.* connected' | awk '{ print $1 }' | xargs)

[ -f /proc/acpi/button/lid/LID0/state ] && LID_STATE=$(grep -oE '[^ ]+$' /proc/acpi/button/lid/LID0/state)

# 	xrandr --setprovideroutputsource modesetting NVIDIA-0

case "${LISTMONITORS}" in
'DP-2-8 DP-2-1')  # home
  DPI=96
  echo "Xft.dpi: ${DPI}" | xrdb -merge
  xrandr --dpi ${DPI} \
    --output eDP-1            --auto --below DP-2-8 --scale 0.5x0.5 \
    --output DP-2-8           --auto --left-of  DP-2-1 \
    --output DP-2-1 --primary --auto
  i3-msg "workspace 8, move workspace to output eDP-1"
  i3-msg "workspace 1, move workspace to output DP-2-1"
  i3-msg "workspace 2, move workspace to output DP-2-8"
  #pkill xautolock ; xset s off ; xset -dpms ; xset s noblank
  ;;
*)
  echo ${LISTMONITORS}
  DPI=220
  echo "Xft.dpi: ${DPI}" | xrdb -merge
  xrandr --dpi ${DPI} --auto
  ;;
esac

if [ $# -eq 1 ]; then
  i3-msg $1
fi

nitrogen --restore
