#!/bin/bash

WALLPAPER_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/backgrounds"
export SWWW_TRANSITION_FPS=60
export SWWW_TRANSITION_STEP=2

# Get the names of all monitors.
MONITORS=$(swww query | grep -Po "^[^:]+")

# Check if swww-daemon is running.
if ! pgrep -x "swww-daemon" > /dev/null; then
  # If swww is not running, start it.
  swww query || swww-daemon -q &
  SWWW_EARLY_RUNNING=0
else
  SWWW_EARLY_RUNNING=1
fi

# Loop indefinitely.
while true; do
  # Loop through each monitor.
  for MONITOR in $MONITORS; do
    # Find a random image file in the wallpaper directory.
    IMAGE=$(find "${WALLPAPER_DIR}" -type f \( -iname "*.jpg" -o -iname "*.png" \) | shuf -n 1)

    # Set the image as the wallpaper for the current monitor.
    swww img --outputs "$MONITOR" "$IMAGE" --resize=crop --transition-type any
  done

  if [ $SWWW_EARLY_RUNNING = 1 ]; then break; fi

  # Sleep for 5 minutes (300 seconds).
  sleep 300
done
