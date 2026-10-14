#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
TEST_DIR=$(mktemp -d)
trap 'rm -rf -- "$TEST_DIR"' EXIT

mkdir -p "$TEST_DIR/bin"
cat > "$TEST_DIR/bin/awww" <<'EOF'
#!/bin/sh

[ "$1" = "query" ] || exit 1
cat <<'OUTPUT'
: eDP-1: 1920x1080, scale: 2, currently displaying: image: /tmp/one.jpg
: DP-1: 2560x1440, scale: 1, currently displaying: image: /tmp/two.jpg
: HDMI-A-1: 1280x720, scale: 1.5, currently displaying: image: /tmp/three.jpg
OUTPUT
EOF
chmod +x "$TEST_DIR/bin/awww"

export PATH="$TEST_DIR/bin:$PATH"
# shellcheck source=../bin/awww.sh
source "$ROOT_DIR/bin/awww.sh"

fail()
{
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

MONITORS=()
MONITOR_SIZES=()
get_monitors

[[ ${MONITORS[*]} == "eDP-1 DP-1 HDMI-A-1" ]] \
    || fail "monitor names were not parsed correctly"
[[ ${MONITOR_SIZES[*]} == "3840x2160 2560x1440 1920x1080" ]] \
    || fail "monitor scales were not applied to render dimensions"

printf 'PASS: awww monitor scale parsing\n'

# Values are read by validate_config in the sourced script.
# shellcheck disable=SC2034
WALLPAPER_SOURCE=local
# shellcheck disable=SC2034
LOCAL_WALLPAPER_DIRS=()
# shellcheck disable=SC2034
REMOTE_WALLPAPER_DIRS=()
# shellcheck disable=SC2034
AWWW_BLURRED_BACKGROUND=false
# shellcheck disable=SC2034
AWWW_METADATA_OVERLAY=false
if validate_config; then
    fail "an empty local wallpaper source passed validation"
fi

printf 'PASS: awww rejects invalid source configuration\n'

# shellcheck disable=SC2034
WALLPAPER_SOURCE=auto
# shellcheck disable=SC2034
LOCAL_WALLPAPER_DIRS=("$TEST_DIR")
# shellcheck disable=SC2034
REMOTE_WALLPAPER_DIRS=("$TEST_DIR/remote")
# shellcheck disable=SC2034
REMOTE_FS_TYPES=""
# shellcheck disable=SC2034
REMOTE_PROBE_TIMEOUT=3
# shellcheck disable=SC2034
REMOTE_SCAN_TIMEOUT=15
# shellcheck disable=SC2034
REMOTE_APPLY_TIMEOUT=10
if validate_config; then
    fail "an invalid remote source passed validation in auto mode"
fi

printf 'PASS: awww rejects invalid remote configuration in auto mode\n'
