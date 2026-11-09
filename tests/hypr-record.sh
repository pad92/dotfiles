#!/usr/bin/env bash
#
# Integration test of hypr-record.sh. wf-recorder, hyprctl, slurp and the
# desktop helpers are replaced by fakes on PATH; jq, flock and /proc are real.
# The fake wf-recorder keeps its name as process name (direct /bin/sh
# shebang), so the script's "is this PID really wf-recorder" guard is
# exercised for real.

set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
RECORD=${RECORD:-"$ROOT_DIR/ansible/roles/dotfiles/files/home/.bin/hypr-record.sh"}
TEST_DIR=$(mktemp -d)
cleanup()
{
    [[ -n ${stranger_pid:-} ]] && kill "$stranger_pid" 2> /dev/null || true
    # A failed case can leave its fake recorder running; it is ours only if
    # the state still names a live process called wf-recorder.
    local pid
    pid=$(sed -n 1p "$TEST_DIR/runtime/hypr-record/state" 2> /dev/null || true)
    if [[ $pid =~ ^[0-9]+$ && $(cat "/proc/$pid/comm" 2> /dev/null) == wf-recorder ]]; then
        kill -KILL "$pid" 2> /dev/null || true
    fi
    rm -rf -- "$TEST_DIR"
}
trap cleanup EXIT

fail()
{
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

BIN="$TEST_DIR/bin"
mkdir -p "$BIN" "$TEST_DIR/runtime"
chmod 700 "$TEST_DIR/runtime"

# Each call appends its arguments, one per line, then a separator line.
# Python, not sh: bash starts background jobs with SIGINT ignored, and a shell
# cannot trap a signal ignored at entry. The real wf-recorder installs its own
# handler, which Python does too. The absolute shebang (no env) keeps the
# process name "wf-recorder".
PYTHON=$(command -v python3) || fail "python3 is required by the fake wf-recorder"
cat > "$BIN/wf-recorder" <<EOF
#!$PYTHON
EOF
cat >> "$BIN/wf-recorder" <<'EOF'
import os
import signal
import sys
import time

# Simulates a slow runner: the process exists, but has not set up anything yet.
time.sleep(float(os.environ.get("MOCK_WF_STARTUP_DELAY", "0")))
arguments = sys.argv[1:]
log = os.environ["MOCK_LOG"]
with open(os.path.join(log, "wf-recorder.args"), "a", encoding="utf-8") as stream:
    stream.write("".join(f"{argument}\n" for argument in arguments) + "--\n")

def option(name):
    return arguments[arguments.index(name) + 1] if name in arguments else None

if option("-c") == os.environ.get("MOCK_WF_FAIL_CODEC"):
    print("cannot open encoder", file=sys.stderr)
    sys.exit(1)
if os.environ.get("MOCK_WF_EXIT_AT_ONCE"):
    sys.exit(int(os.environ["MOCK_WF_EXIT_AT_ONCE"]))
with open(option("-f"), "w", encoding="utf-8") as stream:
    stream.write("fake video")

def stop(signum, frame):
    with open(os.path.join(log, "wf-recorder.signals"), "a", encoding="utf-8") as stream:
        stream.write("INT\n")
    sys.exit(int(os.environ.get("MOCK_WF_EXIT_ON_INT", "0")))

signal.signal(signal.SIGINT, stop)
deadline = time.monotonic() + 30
while time.monotonic() < deadline:
    time.sleep(0.05)
sys.exit(124)
EOF

cat > "$BIN/hyprctl" <<'EOF'
#!/bin/sh
case "$*" in
    "-j monitors") cat "$MOCK_DATA/monitors.json" ;;
    "-j clients") cat "$MOCK_DATA/clients.json" ;;
    *) exit 1 ;;
esac
EOF

cat > "$BIN/slurp" <<'EOF'
#!/bin/sh
cat > "$MOCK_LOG/slurp.stdin"
[ -n "${MOCK_SLURP:-}" ] || exit 1
printf '%s\n' "$MOCK_SLURP"
EOF

cat > "$BIN/notify-send" <<'EOF'
#!/bin/sh
printf '%s\n' "$*" >> "$MOCK_LOG/notify"
EOF

cat > "$BIN/wl-copy" <<'EOF'
#!/bin/sh
cat > "$MOCK_LOG/clipboard"
EOF

# The real pkill would signal the Waybar of the developer's session.
cat > "$BIN/pkill" <<'EOF'
#!/bin/sh
printf '%s\n' "$*" >> "$MOCK_LOG/pkill"
EOF
chmod +x "$BIN"/*

export MOCK_DATA="$TEST_DIR/data"
mkdir -p "$MOCK_DATA"
cat > "$MOCK_DATA/monitors.json" <<'EOF'
[
  {"name": "eDP-1", "focused": false, "activeWorkspace": {"id": 1}, "specialWorkspace": {"id": 0}},
  {"name": "DP-2", "focused": true, "activeWorkspace": {"id": 3}, "specialWorkspace": {"id": -98}}
]
EOF
cat > "$MOCK_DATA/clients.json" <<'EOF'
[
  {"at": [10, 20], "size": [800, 600], "workspace": {"id": 1}, "mapped": true, "hidden": false},
  {"at": [2000, 40], "size": [1280, 720], "workspace": {"id": 3}, "mapped": true, "hidden": false},
  {"at": [5, 5], "size": [300, 200], "workspace": {"id": -98}, "mapped": true, "hidden": false},
  {"at": [0, 0], "size": [640, 480], "workspace": {"id": 2}, "mapped": true, "hidden": false},
  {"at": [1, 1], "size": [50, 50], "workspace": {"id": 1}, "mapped": false, "hidden": false},
  {"at": [2, 2], "size": [60, 60], "workspace": {"id": 3}, "mapped": true, "hidden": true}
]
EOF

export PATH="$BIN:$PATH"
export XDG_RUNTIME_DIR="$TEST_DIR/runtime"
export HYPR_RECORD_DIR="$TEST_DIR/videos"
STATE_FILE="$XDG_RUNTIME_DIR/hypr-record/state"

reset_case()
{
    export MOCK_LOG="$TEST_DIR/log-$1"
    mkdir -p "$MOCK_LOG"
    rm -rf -- "$HYPR_RECORD_DIR" "$XDG_RUNTIME_DIR/hypr-record"
    unset MOCK_SLURP MOCK_WF_EXIT_ON_INT MOCK_WF_EXIT_AT_ONCE MOCK_WF_FAIL_CODEC MOCK_WF_STARTUP_DELAY \
        HYPR_RECORD_HWENC HYPR_RECORD_VAAPI_DEVICE HYPR_RECORD_AUDIO
}

wait_for()
{
    local description=$1 i
    shift
    for ((i = 0; i < 100; i++)); do
        "$@" && return 0
        sleep 0.05
    done
    fail "timed out waiting for $description"
}

recording_started()
{
    [[ -s $STATE_FILE ]] && [[ $(cat "/proc/$(sed -n 1p "$STATE_FILE")/comm" 2> /dev/null) == wf-recorder ]]
}

# Runs `hypr-record.sh $1` in the background until it is recording, then stops
# it with a second identical call, as the key binding does. Sets
# supervisor_status to the exit status of the first call.
record_and_toggle()
{
    local mode=$1 supervisor
    "$RECORD" "$mode" > "$MOCK_LOG/stdout" 2> "$MOCK_LOG/stderr" &
    supervisor=$!
    wait_for "the recording to start" recording_started
    "$RECORD" "$mode"
    supervisor_status=0
    wait "$supervisor" || supervisor_status=$?
}

# Prints the arguments of the Nth wf-recorder call (1-based), one per line.
recorder_call()
{
    awk -v n="$1" '$0 == "--" { call++; next } call == n - 1 { print }' "$MOCK_LOG/wf-recorder.args"
}

has_argument_pair()
{
    local call=$1 option=$2 value=$3
    recorder_call "$call" | awk -v o="$option" -v v="$value" 'previous == o && $0 == v { found = 1 } { previous = $0 } END { exit !found }'
}

recorder_calls()
{
    if [[ -e $MOCK_LOG/wf-recorder.args ]]; then
        grep -c -- '^--$' "$MOCK_LOG/wf-recorder.args" || true
    else
        printf '0\n'
    fi
}

only_file()
{
    local -a files=("$HYPR_RECORD_DIR"/*)
    ((${#files[@]} == 1)) && [[ -e ${files[0]} ]] || return 1
    printf '%s\n' "${files[0]}"
}

# --- Screen: the focused monitor is recorded and the toggle finalizes it.
reset_case screen
record_and_toggle screen
((supervisor_status == 0)) || fail "screen recording exited with $supervisor_status: $(cat "$MOCK_LOG/stderr")"
has_argument_pair 1 -o DP-2 || fail "the focused monitor DP-2 was not recorded"
has_argument_pair 1 -c libx264 || fail "the default encoder is not libx264"
has_argument_pair 1 -r 30 || fail "the default frame rate is not a constant 30 fps"
has_argument_pair 1 -m mp4 || fail "the muxer is not forced to mp4 for the .part name"
! recorder_call 1 | grep -qx -- --audio || fail "audio was recorded although it was not requested"
[[ $(cat "$MOCK_LOG/wf-recorder.signals") == INT ]] \
    || fail "the toggle did not stop wf-recorder with SIGINT"
final=$(only_file) || fail "the recording did not leave exactly one file"
[[ $final == "$HYPR_RECORD_DIR"/rec-*.mp4 && $(cat "$final") == "fake video" ]] \
    || fail "the finished recording was not renamed to .mp4: $final"
[[ $(cat "$MOCK_LOG/stdout") == "$final" ]] || fail "the final path was not printed"
[[ $(cat "$MOCK_LOG/clipboard") == "$final" ]] || fail "the final path was not copied"
[[ ! -e $STATE_FILE ]] || fail "the state file survived a finished recording"
grep -q -- '-RTMIN+8 -x waybar' "$MOCK_LOG/pkill" || fail "Waybar was not told to refresh"

# --- Window: only the windows of visible workspaces are offered to slurp.
reset_case window
export MOCK_SLURP="2000,40 1280x720"
record_and_toggle window
((supervisor_status == 0)) || fail "window recording exited with $supervisor_status"
expected_boxes=$'10,20 800x600\n2000,40 1280x720\n5,5 300x200'
[[ $(cat "$MOCK_LOG/slurp.stdin") == "$expected_boxes" ]] \
    || fail "slurp got the wrong window boxes: $(cat "$MOCK_LOG/slurp.stdin")"
has_argument_pair 1 -g "2000,40 1280x720" || fail "the picked geometry was not recorded"
! recorder_call 1 | grep -qx -- -o || fail "a window recording also selected a whole output"
only_file > /dev/null || fail "the window recording was not saved"

# --- Cancelling the selection creates nothing.
reset_case cancel
"$RECORD" window || fail "cancelling slurp is not a successful no-op"
[[ $(recorder_calls) == 0 ]] || fail "wf-recorder ran after a cancelled selection"
[[ ! -e $STATE_FILE ]] || fail "a cancelled selection left a state file"
[[ ! -e $HYPR_RECORD_DIR ]] || [[ -z $(ls -A "$HYPR_RECORD_DIR") ]] \
    || fail "a cancelled selection left a file"

# --- A malformed selection is refused, not passed to wf-recorder.
reset_case malformed
export MOCK_SLURP="10,10 0x0; rm -rf ~"
status=0
"$RECORD" window 2> /dev/null || status=$?
((status == 1)) || fail "a malformed selection did not fail (status $status)"
[[ $(recorder_calls) == 0 ]] || fail "wf-recorder ran with a malformed selection"

# --- A stale state naming another process never signals that process.
reset_case stale
mkdir -p "$XDG_RUNTIME_DIR/hypr-record"
sleep 30 &
stranger_pid=$!
printf '%s\n%s\n' "$stranger_pid" "$HYPR_RECORD_DIR/rec-old.mp4.part" > "$STATE_FILE"
[[ $("$RECORD" status) == *'"text": ""'* ]] || fail "a stale state was reported as recording"
"$RECORD" stop
kill -0 "$stranger_pid" 2> /dev/null || fail "stop killed a process that is not wf-recorder"
[[ ! -e $STATE_FILE ]] || fail "stop kept a stale state file"
kill "$stranger_pid"
wait "$stranger_pid" 2> /dev/null || true
unset stranger_pid

# --- Status reports a live recording, for the Waybar module.
reset_case status
"$RECORD" screen > /dev/null 2>&1 &
supervisor=$!
wait_for "the recording to start" recording_started
status_json=$("$RECORD" status)
[[ $(jq -r .class <<< "$status_json") == recording && $(jq -r .text <<< "$status_json") == REC ]] \
    || fail "status did not report the live recording: $status_json"
[[ $(jq -r .tooltip <<< "$status_json") == *"$HYPR_RECORD_DIR"/rec-*.mp4* ]] \
    || fail "status did not name the destination file"
"$RECORD" stop
wait "$supervisor" || fail "stopping from Waybar did not finish the recording"
only_file > /dev/null || fail "the recording stopped from Waybar was not saved"

# --- An encoder failure keeps the .part file and never renames it.
reset_case encoder-failure
export MOCK_WF_EXIT_ON_INT=1
record_and_toggle screen
((supervisor_status == 1)) || fail "an encoder failure did not fail the recording"
part=$(only_file) || fail "the failed recording left no file to inspect"
[[ $part == *.mp4.part ]] || fail "a failed recording was renamed: $part"
grep -q 'Screen recording failed' "$MOCK_LOG/notify" || fail "the failure was not notified"
[[ ! -e $STATE_FILE ]] || fail "a failed recording kept its state file"

# --- An encoder that cannot start leaves no empty file behind.
reset_case no-start
export MOCK_WF_EXIT_AT_ONCE=1
status=0
"$RECORD" screen 2> /dev/null || status=$?
((status == 1)) || fail "a recorder that cannot start did not fail"
[[ -z $(ls -A "$HYPR_RECORD_DIR") ]] || fail "a recorder that cannot start left a file"

# --- VAAPI that fails at start falls back to libx264 on the same output.
reset_case hwenc-fallback
export HYPR_RECORD_HWENC=1 HYPR_RECORD_VAAPI_DEVICE=/dev/dri/renderD129 MOCK_WF_FAIL_CODEC=h264_vaapi
"$RECORD" screen > /dev/null 2>&1 &
supervisor=$!
# Stop only the libx264 retry: a stop sent to the failing VAAPI attempt would
# rightly cancel the fallback.
libx264_retry_running()
{
    [[ $(recorder_calls) == 2 ]] && recording_started
}
wait_for "the libx264 retry" libx264_retry_running
"$RECORD" screen
supervisor_status=0
wait "$supervisor" || supervisor_status=$?
((supervisor_status == 0)) || fail "the libx264 fallback recording failed"
[[ $(recorder_calls) == 2 ]] || fail "VAAPI failure was not retried exactly once"
has_argument_pair 1 -d /dev/dri/renderD129 || fail "VAAPI did not use the configured device"
has_argument_pair 2 -c libx264 || fail "the retry did not use libx264"
! recorder_call 2 | grep -qx -- -d || fail "the libx264 retry kept the VAAPI device"
[[ $(only_file) == *.mp4 ]] || fail "the fallback recording was not saved"

# --- A stop sent before wf-recorder handles SIGINT still stops it (slow start).
reset_case slow-start
export MOCK_WF_STARTUP_DELAY=0.5
record_and_toggle screen
((supervisor_status == 0)) || fail "a stop sent during a slow start was lost (status $supervisor_status)"
[[ $(cat "$MOCK_LOG/wf-recorder.signals") == INT ]] || fail "the slow recorder never received SIGINT"
[[ $(only_file) == *.mp4 ]] || fail "the recording stopped during a slow start was not saved"

# --- Stopping while VAAPI starts never restarts a recording with libx264.
reset_case hwenc-stop
export HYPR_RECORD_HWENC=1 HYPR_RECORD_VAAPI_DEVICE=/dev/dri/renderD129 MOCK_WF_EXIT_ON_INT=1
record_and_toggle screen
[[ $(recorder_calls) == 1 ]] || fail "a stopped VAAPI recording was restarted with libx264"
((supervisor_status == 1)) || fail "the interrupted VAAPI failure was not reported"
[[ ! -e $XDG_RUNTIME_DIR/hypr-record/stop-requested ]] || fail "the stop marker survived the recording"

# --- Hardware encoding is never attempted on a guessed device.
reset_case hwenc-no-device
export HYPR_RECORD_HWENC=1
record_and_toggle screen
has_argument_pair 1 -c libx264 || fail "VAAPI was attempted without a configured device"
! recorder_call 1 | grep -qx -- -d || fail "a VAAPI device was guessed"

# --- Audio is opt-in.
reset_case audio
export HYPR_RECORD_AUDIO=1
record_and_toggle screen
recorder_call 1 | grep -qx -- --audio || fail "HYPR_RECORD_AUDIO=1 did not record audio"

# --- Unknown modes are rejected.
reset_case usage
status=0
"$RECORD" region 2> /dev/null || status=$?
((status == 2)) || fail "an unknown mode was not rejected with status 2"

printf 'PASS: hypr-record screen and window recording\n'
