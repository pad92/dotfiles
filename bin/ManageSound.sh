#!/usr/bin/env bash

# Volume management wrapper for PipeWire-Pulse/PulseAudio

function incVol() {
  # Increase volume safely on default sink
  pactl set-sink-mute @DEFAULT_SINK@ false
  pactl set-sink-volume @DEFAULT_SINK@ +5%
}

function decVol() {
  # Decrease volume safely on default sink
  pactl set-sink-mute @DEFAULT_SINK@ false
  pactl set-sink-volume @DEFAULT_SINK@ -5%
}

function muteVol() {
  # Toggle mute state of default sink
  pactl set-sink-mute @DEFAULT_SINK@ toggle
}

function switchAudioSink() {
  # Get all sink names
  local sinks=($(pactl list sinks short | awk '{print $2}'))
  if [ ${#sinks[@]} -le 1 ]; then
    return 0
  fi
  
  # Find currently default/active sink name
  local active_sink=$(pactl get-default-sink 2>/dev/null || pactl info | grep "Default Sink:" | awk '{print $3}')
  if [ -z "$active_sink" ]; then
    return 0
  fi
  
  # Find the next sink in the list to switch to
  local next_sink=""
  for i in "${!sinks[@]}"; do
    if [ "${sinks[$i]}" = "$active_sink" ]; then
      local next_idx=$(( (i + 1) % ${#sinks[@]} ))
      next_sink="${sinks[$next_idx]}"
      break
    fi
  done
  
  # Fallback to first if not found
  if [ -z "$next_sink" ] && [ ${#sinks[@]} -gt 0 ]; then
    next_sink="${sinks[0]}"
  fi
  
  if [ -n "$next_sink" ]; then
    pactl set-default-sink "$next_sink"
  fi
}

function manageSound() {
  case "$1" in
    mute) muteVol ;;
    inc)  incVol ;;
    dec)  decVol ;;
    sw)   switchAudioSink ;;
    *)    echo "Usage: $0 {mute|inc|dec|sw}" >&2; exit 1 ;;
  esac
}

manageSound "$1"
