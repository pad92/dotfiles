#!/usr/bin/env bash
# hyprlock-carousel-idle.sh runs the requested idle action, unless the
# carousel lock screen holds the DPMS inhibit file.

set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
IDLE_SCRIPT="$ROOT_DIR/ansible/roles/dotfiles/files/home/.bin/hyprlock-carousel-idle.sh"
TEST_DIR=$(mktemp -d)
trap 'rm -rf -- "$TEST_DIR"' EXIT

mkdir -p "$TEST_DIR/bin" "$TEST_DIR/runtime"
# The stubs log their own name and arguments when they run.
# shellcheck disable=SC2016
for command in hyprctl systemctl; do
    printf '#!/bin/sh\nprintf "%%s %%s\\n" %s "$*" >> "$MOCK_LOG"\n' "$command" \
        > "$TEST_DIR/bin/$command"
    chmod +x "$TEST_DIR/bin/$command"
done

export PATH="$TEST_DIR/bin:$PATH"
export XDG_RUNTIME_DIR="$TEST_DIR/runtime"
export MOCK_LOG="$TEST_DIR/calls.log"
INHIBIT_FILE="$XDG_RUNTIME_DIR/hyprlock-carousel.dpms-inhibit"

fail()
{
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

: > "$MOCK_LOG"
bash "$IDLE_SCRIPT" dpms
[[ $(cat "$MOCK_LOG") == "hyprctl dispatch hl.dsp.dpms({action = \"off\"})" ]] \
    || fail "dpms did not turn the screens off: $(cat "$MOCK_LOG")"

: > "$MOCK_LOG"
bash "$IDLE_SCRIPT" suspend
[[ $(cat "$MOCK_LOG") == "systemctl suspend" ]] \
    || fail "suspend did not suspend: $(cat "$MOCK_LOG")"

# The carousel lock screen keeps the screens on and the system awake.
: > "$INHIBIT_FILE"
: > "$MOCK_LOG"
bash "$IDLE_SCRIPT" dpms
bash "$IDLE_SCRIPT" suspend
[[ ! -s $MOCK_LOG ]] || fail "an action ran despite the inhibit file: $(cat "$MOCK_LOG")"
rm -f -- "$INHIBIT_FILE"

status=0
bash "$IDLE_SCRIPT" 2> /dev/null || status=$?
[[ $status -eq 2 ]] || fail "a missing action exited with $status instead of 2"
[[ ! -s $MOCK_LOG ]] || fail "a missing action ran a command"

printf 'hyprlock-carousel-idle: ok\n'
