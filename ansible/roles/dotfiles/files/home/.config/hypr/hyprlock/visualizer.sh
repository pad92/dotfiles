#!/bin/sh
# Prints the current frame of the audio visualizer for its hyprlock label, and
# starts visualizer.py when it is not running. No other process is started on
# the hot path: the label runs this script every 50 ms.

[ -n "${XDG_RUNTIME_DIR:-}" ] || exit 0
state_dir="$XDG_RUNTIME_DIR/hyprlock-visualizer"
daemon=${HYPRLOCK_VISUALIZER_DAEMON:-"${0%/*}/visualizer.py"}

pid=
[ -r "$state_dir/pid" ] && IFS= read -r pid < "$state_dir/pid"
case "$pid" in
    ''|*[!0-9]*) pid= ;;
esac
if [ -z "$pid" ] || [ ! -d "/proc/$pid" ]; then
    setsid -f "$daemon" < /dev/null > /dev/null 2>&1
    exit 0
fi

# The frame holds several lines, one per row of the bars. Every line is read,
# including a last one without a trailing newline.
[ -r "$state_dir/frame" ] || exit 0
while IFS= read -r line || [ -n "$line" ]; do
    printf '%s\n' "$line"
done < "$state_dir/frame"
