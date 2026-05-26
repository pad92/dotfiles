#!/usr/bin/env bash

WALLPAPER_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/backgrounds"
export AWWW_TRANSITION_FPS=30
export AWWW_TRANSITION_STEP=10

# Get the names of all monitors.
QUERY=$(awww query 2>/dev/null || true)
if [ -z "$QUERY" ]; then
  exit 0
fi
MONITORS=$(echo "$QUERY" | sed -E 's/^: ([^:]+):.*/\1/')

for MONITOR in ${MONITORS}; do
  # Find a random image file in the wallpaper directory.
  IMAGE=$(find -L "${WALLPAPER_DIR}" -type f \( -iname "*.jpg" -o -iname "*.png" \) | shuf -n 1)

  # Set the image as the wallpaper for the current monitor.
  awww img --outputs "${MONITOR}" "${IMAGE}" --resize=crop --transition-type fade
done
