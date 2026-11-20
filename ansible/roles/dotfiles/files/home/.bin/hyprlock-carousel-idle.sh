#!/usr/bin/env bash
# Hypridle action, skipped while the carousel lock screen runs:
# "dpms" turns the screens off, "suspend" suspends the system.

set -uo pipefail

DPMS_INHIBIT_FILE="${XDG_RUNTIME_DIR:-${HOME}/.cache}/hyprlock-carousel.dpms-inhibit"

if [ -e "${DPMS_INHIBIT_FILE}" ]; then
    exit 0
fi

case "${1:-}" in
    dpms) exec hyprctl dispatch 'hl.dsp.dpms({action = "off"})' ;;
    suspend) exec systemctl suspend ;;
    *)
        printf 'Usage: %s dpms|suspend\n' "${0##*/}" >&2
        exit 2
        ;;
esac
