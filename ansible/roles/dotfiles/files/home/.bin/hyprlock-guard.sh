#!/usr/bin/env bash

set -uo pipefail

if [ "$#" -eq 0 ]; then
    printf 'Usage: %s COMMAND [ARGUMENT ...]\n' "$0" >&2
    exit 2
fi

LOCK_DIR="${XDG_RUNTIME_DIR:-${HOME}/.cache}"
LOCK_FILE="${LOCK_DIR}/hyprlock.lock"

mkdir -p "${LOCK_DIR}" || exit 1
if ! command -v flock >/dev/null 2>&1; then
    printf "Error: 'flock' is not installed or not found in PATH.\n" >&2
    exit 1
fi

exec 9> "${LOCK_FILE}" || exit 1
flock -n 9 || exit 0

if pgrep -u "$(id -u)" -x hyprlock >/dev/null 2>&1; then
    exit 0
fi

exec "$@"
