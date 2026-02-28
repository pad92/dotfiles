#!/bin/sh

# Exit on error
set -e

# --- Environment Setup ---
USER_ID=$(id -u)
RUNTIME_DIR="/run/user/$USER_ID"

if [ -d "$RUNTIME_DIR/hypr" ]; then
  export HYPRLAND_INSTANCE_SIGNATURE=$(ls -t "$RUNTIME_DIR/hypr" | head -n 1)
  export XDG_RUNTIME_DIR="$RUNTIME_DIR"
fi
# -------------------------

# Function to log messages
log_message() {
  echo "[$(basename "$0")] $1"
}

# Function to handle errors
handle_error() {
  log_message "ERROR: $1"
  exit 1
}

# Validate input
if [ $# -ne 1 ]; then
  handle_error "Usage: $0 {start|end}"
fi

case "$1" in
  start)
    log_message "Starting GameMode"
    if [ -z "$HYPRLAND_INSTANCE_SIGNATURE" ]; then
      log_message "Warning: Hyprland signature not found. Skipping hyprctl."
    else
      notify-send "🚀 GameMode" "Optimizing..."
      # Désactive animations, ombres ET flou (blur)
      if ! hyprctl --batch "keyword animations:enabled 0; keyword decoration:shadow:enabled 0; keyword decoration:blur:enabled 0"; then
        handle_error "Failed to configure Hyprland settings"
      fi
    fi

    if ! systemctl --user stop hypridle.service; then
      log_message "Warning: Failed to stop hypridle.service"
    fi
    ;;

  end)
    log_message "Ending GameMode"
    if [ -z "$HYPRLAND_INSTANCE_SIGNATURE" ]; then
      log_message "Warning: Hyprland signature not found. Cannot reload."
    else
      notify-send "🎮 Desktop Mode" "Restoring..."
      if ! hyprctl reload; then
        handle_error "Failed to reload Hyprland configuration"
      fi
    fi

    if ! systemctl --user is-active hypridle.service >/dev/null 2>&1; then
      log_message "Restarting hypridle.service..."
      systemctl --user reset-failed hypridle.service 2>/dev/null || true
      if ! systemctl --user start hypridle.service; then
        log_message "Warning: Failed to start hypridle.service"
      fi
    fi
    ;;

  *)
    handle_error "Invalid argument: $1. Use 'start' or 'end'"
    ;;
esac
