#!/usr/bin/env bash

# Safety flags
set -uo pipefail

WALLPAPER_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/backgrounds"
export AWWW_TRANSITION_FPS=30
export AWWW_TRANSITION_STEP=10

# 1. Verify wallpaper directory exists
if [ ! -d "${WALLPAPER_DIR}" ]; then
    echo "Error: Wallpaper directory '${WALLPAPER_DIR}' does not exist." >&2
    exit 1
fi

# 2. Check if awww command is available
if ! command -v awww >/dev/null 2>&1; then
    echo "Error: 'awww' is not installed or not found in PATH." >&2
    exit 1
fi

# 3. Wait for daemon to respond (Actual 10-second timeout)
TIMEOUT_ATTEMPTS=50  # 50 * 0.2s = 10s
while ! awww query >/dev/null 2>&1; do
    sleep 0.2
    TIMEOUT_ATTEMPTS=$((TIMEOUT_ATTEMPTS - 1))
    if [ "${TIMEOUT_ATTEMPTS}" -le 0 ]; then
        echo "Error: awww-daemon did not respond after 10 seconds." >&2
        exit 1
    fi
done

# 4. Get active monitors
QUERY=$(awww query 2>/dev/null)
if [ -z "$QUERY" ]; then
    exit 1
fi

# Extract monitor list reliably
mapfile -t MONITORS < <(echo "$QUERY" | sed -E 's/^: ([^:]+):.*/\1/')

if [ ${#MONITORS[@]} -eq 0 ]; then
    exit 0
fi

# 5. Find and shuffle all wallpapers once using null-delimited strings (safe for spaces)
mapfile -d '' IMAGES < <(find -L "${WALLPAPER_DIR}" -type f \( -iname "*.jpg" -o -iname "*.png" \) -print0 2>/dev/null | shuf -z)

if [ ${#IMAGES[@]} -eq 0 ]; then
    echo "Warning: No .jpg or .png files found in '${WALLPAPER_DIR}'." >&2
    exit 1
fi

# 6. Apply wallpapers (different random image per monitor)
IMAGE_INDEX=0
for MONITOR in "${MONITORS[@]}"; do
    # Get a random image (wrap around if there are more monitors than images)
    IMAGE="${IMAGES[IMAGE_INDEX % ${#IMAGES[@]}]}"
    
    if [ -n "${IMAGE}" ]; then
        awww img --outputs "${MONITOR}" "${IMAGE}" --resize=crop --transition-type fade
    fi
    IMAGE_INDEX=$((IMAGE_INDEX + 1))
done