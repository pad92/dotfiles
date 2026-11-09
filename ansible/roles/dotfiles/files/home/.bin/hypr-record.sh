#!/usr/bin/env bash
#
# hypr-record.sh - Record a light video of a screen or a window under Hyprland.
#
# The recording is a small H.264 MP4 (30 fps, no audio by default) that plays
# in any browser or chat client. Frames are copied continuously, so a still
# screen records correctly; encoding a 1440p screen takes about 1.5 cores. A screen/window call starts a recording; the
# same call while a recording runs stops it, so one key binding toggles it.
#
# Usage:
#   hypr-record.sh screen   record the focused monitor
#   hypr-record.sh window   click a window, or drag a region, to record it
#   hypr-record.sh stop     stop the running recording, if any
#   hypr-record.sh status   print the Waybar JSON of the recording state
#
# The process that starts wf-recorder stays in the foreground and supervises
# it: when wf-recorder ends, it renames the `.mp4.part` file to `.mp4` only if
# the encoder succeeded, copies the path to the clipboard and notifies. A
# failed recording keeps its `.part` file for inspection and is never renamed.
#
# A window is recorded as the fixed region it covered when it was picked:
# moving it takes it out of the frame, and windows above it are recorded too.
#
# Environment:
#   HYPR_RECORD_DIR           output directory
#                             (default: $(xdg-user-dir VIDEOS)/Recordings)
#   HYPR_RECORD_FPS           constant frame rate (default: 30)
#   HYPR_RECORD_CRF           libx264 quality, higher is smaller (default: 28)
#   HYPR_RECORD_AUDIO         1: also record the default audio source
#   HYPR_RECORD_HWENC         1: encode with VAAPI on HYPR_RECORD_VAAPI_DEVICE;
#                             if it fails at start, fall back to libx264
#   HYPR_RECORD_VAAPI_DEVICE  VAAPI render node, for example /dev/dri/renderD128.
#                             There is no default: the right node depends on
#                             the GPU of each machine.

set -euo pipefail

readonly RECORDER=wf-recorder
readonly WAYBAR_SIGNAL=8
# A hardware encoder that dies sooner than this is treated as unusable.
readonly HWENC_STARTUP_SECONDS=3
# How many times, one second apart, the stop call sends SIGINT.
readonly STOP_ATTEMPTS=10

runtime_root=${XDG_RUNTIME_DIR:-}
if [[ -z $runtime_root || ! -d $runtime_root ]]; then
    printf 'hypr-record: XDG_RUNTIME_DIR is not set\n' >&2
    exit 1
fi
readonly STATE_DIR="$runtime_root/hypr-record"
readonly STATE_FILE="$STATE_DIR/state"
readonly LOCK_FILE="$STATE_DIR/lock"
readonly LOG_FILE="$STATE_DIR/$RECORDER.log"
# Written by the stop call, so the supervisor never restarts a recording the
# user asked to stop.
readonly STOP_MARKER="$STATE_DIR/stop-requested"

fps=${HYPR_RECORD_FPS:-30}
crf=${HYPR_RECORD_CRF:-28}
[[ $fps =~ ^[1-9][0-9]*$ ]] || { printf 'hypr-record: invalid HYPR_RECORD_FPS\n' >&2; exit 2; }
[[ $crf =~ ^[0-9]+$ ]] || { printf 'hypr-record: invalid HYPR_RECORD_CRF\n' >&2; exit 2; }

usage()
{
    printf 'usage: %s screen|window|stop|status\n' "${0##*/}" >&2
}

notify()
{
    local urgency=$1
    shift
    if command -v notify-send > /dev/null 2>&1; then
        notify-send -u "$urgency" -a "Screen recording" "$@" || true
    fi
}

fail()
{
    printf 'hypr-record: %s\n' "$1" >&2
    notify critical "Screen recording failed" "$1"
    exit 1
}

refresh_waybar()
{
    pkill "-RTMIN+$WAYBAR_SIGNAL" -x waybar > /dev/null 2>&1 || true
}

# Prints the PID of the running recording. Succeeds only when the state file
# names a live wf-recorder process: a recycled PID is never trusted.
recording_pid()
{
    local pid comm
    [[ -r $STATE_FILE ]] || return 1
    pid=$(sed -n 1p "$STATE_FILE")
    [[ $pid =~ ^[1-9][0-9]*$ ]] || return 1
    comm=$(cat "/proc/$pid/comm" 2> /dev/null) || return 1
    [[ $comm == "$RECORDER" ]] || return 1
    printf '%s\n' "$pid"
}

print_status()
{
    local path
    if recording_pid > /dev/null; then
        path=$(sed -n 2p "$STATE_FILE")
        jq -cn --arg path "${path%.part}" \
            '{text: "REC", class: "recording", tooltip: ("Recording to " + $path + "\nClick to stop")}'
    else
        printf '{"text": "", "class": "idle"}\n'
    fi
}

stop_recording()
{
    local pid
    local attempt tick
    if pid=$(recording_pid); then
        : > "$STOP_MARKER"
        # SIGINT lets wf-recorder write the MP4 index before it exits. A
        # background job starts with SIGINT ignored until wf-recorder installs
        # its handler, so a signal sent right after the start can be lost:
        # send it again until the process is gone.
        for ((attempt = 0; attempt < STOP_ATTEMPTS; attempt++)); do
            kill -INT "$pid" 2> /dev/null || return 0
            for ((tick = 0; tick < 10; tick++)); do
                sleep 0.1
                [[ $(cat "/proc/$pid/comm" 2> /dev/null) == "$RECORDER" ]] || return 0
            done
        done
        fail "$RECORDER (PID $pid) did not stop after $STOP_ATTEMPTS SIGINT"
    fi
    # The state is stale (supervisor killed, PID gone or recycled). Forget it;
    # the recording file itself, if any, is left where it is.
    rm -f -- "$STATE_FILE"
    refresh_waybar
}

require()
{
    local command
    for command in "$@"; do
        command -v "$command" > /dev/null 2>&1 || fail "$command is not installed"
    done
}

focused_monitor()
{
    hyprctl -j monitors | jq -r 'first(.[] | select(.focused) | .name) // empty'
}

# Boxes of the windows shown on the visible workspaces, in the "x,y WxH"
# format slurp reads on its standard input.
visible_window_boxes()
{
    local monitors
    monitors=$(hyprctl -j monitors)
    hyprctl -j clients | jq -r --argjson monitors "$monitors" '
        ($monitors | map(.activeWorkspace.id, .specialWorkspace.id)
            | map(select(. != null and . != 0))) as $visible
        | .[]
        | select(.mapped and (.hidden | not))
        | select(.workspace.id as $id | $visible | index($id))
        | "\(.at[0]),\(.at[1]) \(.size[0])x\(.size[1])"'
}

# Prints the picked "x,y WxH" region. Returns 1 when the user cancels and 2
# when the windows cannot be listed or slurp answers something unexpected.
pick_geometry()
{
    local boxes geometry
    boxes=$(visible_window_boxes) || return 2
    # slurp snaps a click to one of the boxes and still allows dragging a
    # free region. Escape makes it fail, which cancels the recording.
    geometry=$(printf '%s' "$boxes" | slurp) || return 1
    if [[ ! $geometry =~ ^-?[0-9]+,-?[0-9]+\ [1-9][0-9]*x[1-9][0-9]*$ ]]; then
        printf 'hypr-record: unexpected selection from slurp: %s\n' "$geometry" >&2
        return 2
    fi
    printf '%s\n' "$geometry"
}

output_directory()
{
    local videos
    if [[ -n ${HYPR_RECORD_DIR:-} ]]; then
        printf '%s\n' "$HYPR_RECORD_DIR"
        return
    fi
    videos=$(xdg-user-dir VIDEOS 2> /dev/null || true)
    # xdg-user-dir answers $HOME when the directory is not configured.
    if [[ -z $videos || $videos == "$HOME" ]]; then
        videos="$HOME/Videos"
    fi
    printf '%s/Recordings\n' "$videos"
}

software_encoder=(
    # superfast gives the size of veryfast with about 20% less CPU at 1440p.
    -c libx264 -x yuv420p -p preset=superfast -p "crf=$crf"
    # Drop frames to the target rate first, so the crop only runs on kept
    # frames. yuv420p needs even dimensions; a window or a scaled output can
    # be odd.
    -F "fps=$fps,crop=trunc(iw/2)*2:trunc(ih/2)*2"
)

# Runs wf-recorder until it exits and stores its exit status in
# `recorder_status`. The state file names its PID for the stop call.
run_recorder()
{
    local -a encoder=("$@")
    local -a audio=()
    [[ ${HYPR_RECORD_AUDIO:-0} == 1 ]] && audio=(--audio)

    # -D copies frames continuously. With damage tracking, a still screen
    # gives wf-recorder almost no frames: the MP4 is left unreadable and
    # SIGINT waits for the next screen update.
    "$RECORDER" -D "${target[@]}" "${encoder[@]}" "${audio[@]}" -r "$fps" \
        -m mp4 -y -f "$part" < /dev/null >> "$LOG_FILE" 2>&1 9>&- &
    recorder_pid=$!
    printf '%s\n%s\n' "$recorder_pid" "$part" > "$STATE_FILE"
    release_lock
    refresh_waybar

    recorder_status=0
    wait "$recorder_pid" || recorder_status=$?
    # A trapped signal interrupts `wait` before the recorder has exited.
    while kill -0 "$recorder_pid" 2> /dev/null; do
        recorder_status=0
        wait "$recorder_pid" || recorder_status=$?
    done
}

# Without argument, gives up at once: another call is selecting or switching
# state, so this key press is ignored. With a number, waits that many seconds.
acquire_lock()
{
    exec 9> "$LOCK_FILE"
    if [[ -n ${1:-} ]]; then
        flock -w "$1" 9 || fail "the recording state is locked"
    else
        flock -n 9 || exit 0
    fi
}

release_lock()
{
    exec 9>&-
}

forward_stop()
{
    [[ -n ${recorder_pid:-} ]] && kill -INT "$recorder_pid" 2> /dev/null || true
}

cleanup()
{
    local pid
    pid=$(sed -n 1p "$STATE_FILE" 2> /dev/null || true)
    if [[ -n ${recorder_pid:-} && $pid == "$recorder_pid" ]]; then
        rm -f -- "$STATE_FILE" "$STOP_MARKER"
    fi
    refresh_waybar
}

start_recording()
{
    local mode=$1 monitor geometry directory stamp final suffix=0 started

    require "$RECORDER" hyprctl jq
    case $mode in
        screen)
            monitor=$(focused_monitor)
            [[ -n $monitor ]] || fail "no focused monitor"
            target=(-o "$monitor")
            ;;
        window)
            require slurp
            geometry=$(pick_geometry) || {
                (($? == 1)) && exit 0
                fail "could not select a window"
            }
            target=(-g "$geometry")
            ;;
    esac

    directory=$(output_directory)
    mkdir -p -- "$directory"
    stamp=$(date +%Y%m%d-%H%M%S)
    final="$directory/rec-$stamp.mp4"
    while [[ -e $final || -e $final.part ]]; do
        suffix=$((suffix + 1))
        final="$directory/rec-$stamp-$suffix.mp4"
    done
    part="$final.part"
    : > "$LOG_FILE"
    rm -f -- "$STOP_MARKER"

    trap cleanup EXIT
    trap forward_stop INT TERM HUP

    started=$SECONDS
    if [[ ${HYPR_RECORD_HWENC:-0} == 1 && -n ${HYPR_RECORD_VAAPI_DEVICE:-} ]]; then
        run_recorder -c h264_vaapi -d "$HYPR_RECORD_VAAPI_DEVICE"
        if ((recorder_status != 0 && SECONDS - started < HWENC_STARTUP_SECONDS)) \
            && [[ ! -e $STOP_MARKER ]]; then
            notify normal "Hardware encoding failed" "Recording again with libx264"
            rm -f -- "$part"
            acquire_lock 5
            run_recorder "${software_encoder[@]}"
        fi
    else
        if [[ ${HYPR_RECORD_HWENC:-0} == 1 ]]; then
            notify normal "Hardware encoding skipped" \
                "HYPR_RECORD_VAAPI_DEVICE is not set; using libx264"
        fi
        run_recorder "${software_encoder[@]}"
    fi

    if ((recorder_status != 0)) || [[ ! -s $part ]]; then
        [[ -e $part && ! -s $part ]] && rm -f -- "$part"
        fail "$RECORDER exited with status $recorder_status, see $LOG_FILE"
    fi
    # Recent coreutils make `mv -n` fail when it skips; the check below decides.
    mv -n -- "$part" "$final" || true
    [[ -e $final && ! -e $part ]] || fail "could not rename $part"

    if command -v wl-copy > /dev/null 2>&1; then
        printf '%s' "$final" | wl-copy || true
    fi
    notify normal "Recording saved" "$final"
    printf '%s\n' "$final"
}

main()
{
    local mode=${1:-}
    case $mode in
        screen | window | stop | status) ;;
        *)
            usage
            exit 2
            ;;
    esac
    mkdir -p -- "$STATE_DIR"

    if [[ $mode == status ]]; then
        print_status
        return
    fi

    acquire_lock
    if [[ $mode == stop ]] || recording_pid > /dev/null; then
        stop_recording
        return
    fi
    start_recording "$mode"
}

main "$@"
