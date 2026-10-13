#!/usr/bin/env bash

set -uo pipefail

DPMS_INHIBIT_FILE="${XDG_RUNTIME_DIR:-${HOME}/.cache}/hyprlock-carousel.dpms-inhibit"

if [ -e "${DPMS_INHIBIT_FILE}" ]; then
    exit 0
fi

exec hyprctl dispatch 'hl.dsp.dpms({action = "off"})'
