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
INPUT=`echo -e "Lock\nLogout\nShutdown\nReboot\nSuspend\nScreen off\n$DPMS\n$NETWORK\nSwitch audio\nMute" | dmenu -i -nb '#C31616' -sb '#404040' -nf white`

case "$INPUT" in
	"Lock")         i3lock-fancy -t '' ;;
    "Logout")       loginctl terminate-session $(cat /proc/self/sessionid) ;;
	"Shutdown")     sudo shutdown -P now ;;
	"Reboot")       sudo shutdown -r now ;;
	"Suspend")      i3lock-fancy -t '' && systemctl suspend ;;
	"Screen off")   i3lock-fancy -t '' && xset dpms force off ;;
	"DPMS: on")     xset -dpms s off ;;
	"DPMS: off")    xset +dpms s on ;;
	"Network: on")  nmcli networking off ;;
	"Network: off") nmcli networking on ;;
	"Mute")         $HOME/.bin/ManageSound.sh "mute" ;;
	"Switch audio") $HOME/.bin/ManageSound.sh "sw" ;;
esac
