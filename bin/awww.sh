#!/bin/bash

WALLPAPER_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/backgrounds"
export AWWW_TRANSITION_FPS=1
export AWWW_TRANSITION_STEP=255

# Get the names of all monitors.
MONITORS=$(awww query | grep -Po "^[^:]+")
MONITORS=$(awww query | sed -E 's/^: ([^:]+):.*/\1/')

for MONITOR in ${MONITORS}; do
  # Find a random image file in the wallpaper directory.
  IMAGE=$(find -L "${WALLPAPER_DIR}" -type f \( -iname "*.jpg" -o -iname "*.png" \) | shuf -n 1)

  # Set the image as the wallpaper for the current monitor.
  awww img --outputs "${MONITOR}" "${IMAGE}" --resize=crop --transition-type simple
done
