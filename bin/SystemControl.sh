#!/bin/bash

function toggleDPMS() {
  state="$(xset q | grep "DPMS is" | awk '{print $NF}')"
  if [[ "$state" == "Enabled" ]]; then
    echo "DPMS: on"
  else
    echo "DPMS: off"
  fi
}

function toggleNetwork() {
  state="$(nmcli networking connectivity check)"
  if [[ "$state" == "full" ]]; then
    echo "Network: on"
  else
    echo "Network: off"
  fi
}

DPMS="$(toggleDPMS)"
NETWORK="$(toggleNetwork)"
INPUT=$(echo -e "Lock\nLogout\nShutdown\nReboot\nReboot Windows\nSuspend\nScreen off\n$DPMS\n$NETWORK\nSwitch audio\nMute" | dmenu -i -nb '#C31616' -sb '#404040' -nf white)

case "$INPUT" in
"Lock")
  sleep 1
  i3lock-fancy -p -t ''
  ;;
"Logout") i3exit logout ;;
"Shutdown") i3exit shutdown ;;
"Reboot") i3exit reboot ;;
"Reboot Windows") systemctl reboot --boot-loader-entry=auto-windows ;;
"Suspend")
  sleep 1
  i3lock-fancy -p -t '' && systemctl suspend
  ;;
"Screen off")
  sleep 1
  i3lock-fancy -p -t '' && xset dpms force off
  ;;
"DPMS: on") xset -dpms s off ;;
"DPMS: off") xset +dpms s on ;;
"Network: on") nmcli networking off ;;
"Network: off") nmcli networking on ;;
"Mute") $HOME/.bin/ManageSound.sh "mute" ;;
"Switch audio") $HOME/.bin/ManageSound.sh "sw" ;;
esac
