#!/bin/sh

LISTMONITORS=$(xrandr --current --listmonitors | grep -v '^Monitors' | awk '{print $NF}' | sort | tr '\n' ' ' | sed 's/ $//g')

[ -f /proc/acpi/button/lid/LID0/state ] && LID_STATE=$(grep -oE '[^ ]+$' /proc/acpi/button/lid/LID0/state)

# 	xrandr --setprovideroutputsource modesetting NVIDIA-0

case "${LISTMONITORS}" in
'DP-1-1 DP-1-2 eDP-1')  # anker @ home
  xrandr --dpi 96 \
    --output eDP-1 --off \
    --output DP-1-1 --auto --pos 0x0 --rotate right \
    --output DP-1-2 --primary --auto --pos 1080x0 --rotate normal
  i3-msg "workspace 1, move workspace to output DP-1-2"
  i3-msg "workspace 2, move workspace to output DP-1-1"
  pkill xautolock
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
