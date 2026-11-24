#!/bin/sh
# Prints the current frame of the audio visualizer for its hyprlock label, and
# starts visualizer.py when it is not running. No other process is started on
# the hot path: the label runs this script every 50 ms.

[ -n "${XDG_RUNTIME_DIR:-}" ] || exit 0
state_dir="$XDG_RUNTIME_DIR/hyprlock-visualizer"
daemon=${HYPRLOCK_VISUALIZER_DAEMON:-"${0%/*}/visualizer.py"}

# The daemon is alive when its pid file names a process that started at the
# recorded time: the pid alone may since belong to another process.
alive() {
    pid='' start='' stat=''
    [ -r "$state_dir/pid" ] || return 1
    { IFS= read -r pid; IFS= read -r start; } < "$state_dir/pid"
    case "$pid" in ''|*[!0-9]*) return 1 ;; esac
    case "$start" in ''|*[!0-9]*) return 1 ;; esac
    { IFS= read -r stat < "/proc/$pid/stat"; } 2> /dev/null || return 1
    # Field 22 is the start time. The command name before it, in parentheses,
    # may hold spaces, so split after its closing parenthesis.
    set -f
    # shellcheck disable=SC2086 # the fields are split on purpose
    set -- ${stat##*) }
    [ $# -ge 20 ] || return 1
    shift 19
    [ "$1" = "$start" ]
}

if ! alive; then
    setsid -f "$daemon" < /dev/null > /dev/null 2>&1
    exit 0
fi

# The frame holds several lines, one per row of the bars. Every line is read,
# including a last one without a trailing newline.
[ -r "$state_dir/frame" ] || exit 0
while IFS= read -r line || [ -n "$line" ]; do
    printf '%s\n' "$line"
done < "$state_dir/frame"
