#!/bin/bash

WALLPAPER_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/backgrounds"
export SWWW_TRANSITION_FPS=60
export SWWW_TRANSITION_STEP=2

# Get the names of all monitors.
MONITORS=$(swww query | grep -Po "^[^:]+")

for MONITOR in $MONITORS; do
  # Find a random image file in the wallpaper directory.
  IMAGE=$(find -L "${WALLPAPER_DIR}" -type f \( -iname "*.jpg" -o -iname "*.png" \) | shuf -n 1)

  # Set the image as the wallpaper for the current monitor.
  swww img --outputs "$MONITOR" "$IMAGE" --resize=crop --transition-type random
done
