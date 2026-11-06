#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
TEST_DIR=$(mktemp -d)
trap 'rm -rf -- "$TEST_DIR"' EXIT

fail()
{
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

mkdir -p "$TEST_DIR/bin"
export PATH="$TEST_DIR/bin:$PATH"

export DOTFILES_REPOSITORY="$ROOT_DIR"
# shellcheck source=../ansible/roles/dotfiles/files/home/.bin/hypr-screenshot.sh
source "$ROOT_DIR/ansible/roles/dotfiles/files/home/.bin/hypr-screenshot.sh"
set +e # the sourced script enables errexit; each check below handles errors

# --- Settings are validated before anything starts -------------------------
accepts()
{
    (RES="$1" WEBP_QUALITY="$2" SETTLE="$3" DEMO_QUERY="${4:-fire}" \
        DEMO_WIDTH="${5:-1280}" validate_settings) >/dev/null 2>&1
}

accepts 1920x1080 80 2 || fail "valid settings were rejected"
accepts 2560x1440 100 0.5 || fail "a fractional SETTLE was rejected"
accepts 1920 80 2 && fail "a RES without height was accepted"
accepts 0x1080 80 2 && fail "a zero-width RES was accepted"
accepts 1920x1080 101 2 && fail "WEBP_QUALITY above 100 was accepted"
accepts 1920x1080 08 2 || fail "a zero-padded WEBP_QUALITY was rejected"
accepts 1920x1080 high 2 && fail "a non-numeric WEBP_QUALITY was accepted"
accepts 1920x1080 80 -1 && fail "a negative SETTLE was accepted"
accepts 1920x1080 80 2 term2 || fail "a lowercase alphanumeric DEMO_QUERY was rejected"
accepts 1920x1080 80 2 'fire fox' && fail "a DEMO_QUERY with a space was accepted"
accepts 1920x1080 80 2 'x"})' && fail "a DEMO_QUERY with Lua syntax was accepted"
accepts 1920x1080 80 2 fire 0 && fail "a zero DEMO_WIDTH was accepted"
(RES=1920x1080 WEBP_QUALITY=80 SETTLE=2 HYPR_CONFIG_DIR="$TEST_DIR/missing" \
    validate_settings) >/dev/null 2>&1 \
    && fail "a config directory without hyprland.lua was accepted"
for editor_file in /etc/hostname ../README.md missing.md; do
    (EDITOR_FILE="$editor_file" validate_settings) >/dev/null 2>&1 \
        && fail "EDITOR_FILE '$editor_file' outside the repository was accepted"
done

printf 'PASS: hypr-screenshot settings validation\n'

# --- The demo home holds no trace of the real user ---------------------------
WORK_DIR="$TEST_DIR/work"
mkdir -p "$WORK_DIR"
real_user=$(id -un)
write_identity "$WORK_DIR"
[[ $(cut -d: -f1 "$WORK_DIR/passwd" | paste -sd,) == root,demo ]] \
    || fail "the sandbox passwd names other users: $(<"$WORK_DIR/passwd")"
grep -qF -- "$real_user" "$WORK_DIR/passwd" "$WORK_DIR/group" \
    && fail "the sandbox identity files name the real user"

home="$WORK_DIR/home"
(build_demo_home "$home") || fail "the demo home could not be built"
for rendered in .zshrc .config/hypr/hyprlock.conf; do
    [[ -f $home/$rendered && ! -L $home/$rendered ]] \
        || fail "$rendered was not rendered into the demo home"
    grep -qE '\{\{|\{%' "$home/$rendered" && fail "$rendered kept a template expression"
done
grep -qx 'ZSH="/home/demo/.local/share/dotfiles/zsh"' "$home/.zshrc" \
    || fail "the zshrc does not load zsh from the role's link destination"
while IFS= read -r link; do
    target=$(readlink "$link")
    [[ $target == /home/demo/.dotfiles/* ]] \
        || fail "$link points outside the mounted repository: $target"
    [[ -e $ROOT_DIR/${target#/home/demo/.dotfiles/} ]] \
        || fail "$link points to a missing repository file: $target"
done < <(find "$home" -type l)
[[ -L $home/.config/waybar/config ]] || fail "the demo home has no Waybar config"
grep -rqF -- "/home/$real_user" "$home" && fail "the demo home mentions the real home"

printf 'PASS: hypr-screenshot demo home\n'

# --- Clients only receive the sandbox environment --------------------------
export HYPR_SCREENSHOT_SENTINEL=leaked
# Both are read by sandbox_env in the sourced script.
# shellcheck disable=SC2034
NESTED_WAYLAND=/run/user/1000/wayland-9
# shellcheck disable=SC2034
SIG=showcase_sig
mapfile -t client_env < <(sandbox_env unix:path=/tmp/bus)
allowed=" HOME USER LOGNAME SHELL PATH LANG XDG_RUNTIME_DIR XDG_SESSION_TYPE \
XDG_CURRENT_DESKTOP WAYLAND_DISPLAY HYPRLAND_INSTANCE_SIGNATURE DBUS_SESSION_BUS_ADDRESS "
for pair in "${client_env[@]}"; do
    [[ $allowed == *" ${pair%%=*} "* ]] || fail "unexpected client variable: $pair"
done
[[ " ${client_env[*]} " == *" USER=demo "* && " ${client_env[*]} " == *" HOME=/home/demo "* ]] \
    || fail "clients do not run as the demo user: ${client_env[*]}"
[[ " ${client_env[*]} " != *"$real_user"* ]] || fail "the client environment names the real user"

printf 'PASS: hypr-screenshot client environment\n'

# --- The entry config skips startup hooks and loads the repo modules -------
if command -v lua >/dev/null 2>&1; then
    config_dir="$TEST_DIR/hypr config"
    mkdir -p "$config_dir/conf"
    cat >"$config_dir/conf/module.lua" <<'EOF'
LOADED_MODULE = true
EOF
    cat >"$config_dir/hyprland.lua" <<'EOF'
local hl = rawget(_G, "hl")
require("conf.module")
hl.on("hyprland.start", function() end)
hl.on("window.open", function() end)
EOF
    write_entry_config "$config_dir" "$TEST_DIR/entry.lua"

    result=$(lua - "$TEST_DIR/entry.lua" <<'EOF'
local events, config = {}, nil
local original_on = function(event) events[#events + 1] = event end
hl = { on = original_on, config = function(c) config = c end }
dofile(arg[1])
print(table.concat(events, ","))
print(tostring(LOADED_MODULE))
print(tostring(config.animations.enabled))
print(tostring(config.cursor.invisible))
print(tostring(config.misc.force_default_wallpaper))
print(tostring(hl.on == original_on))
EOF
    ) || fail "the generated entry config did not run"

    expected=$'window.open\ntrue\nfalse\ntrue\n2\ntrue'
    [[ $result == "$expected" ]] \
        || fail "unexpected entry config behaviour: $(printf '%q' "$result")"
    printf 'PASS: hypr-screenshot entry config isolation\n'
else
    printf 'SKIP: hypr-screenshot entry config isolation (lua not installed)\n'
fi

# --- The instance is matched by PID, not by a before/after diff -------------
cat >"$TEST_DIR/bin/hyprctl" <<'EOF'
#!/bin/sh
cat <<'JSON'
[{"instance":"live_1","pid":100,"wl_socket":"wayland-1"},
 {"instance":"showcase_2","pid":4242,"wl_socket":"wayland-2"}]
JSON
EOF
chmod +x "$TEST_DIR/bin/hyprctl"

[[ $(instance_for_pid 4242) == showcase_2 ]] \
    || fail "the showcase instance was not found by PID"
[[ -z $(instance_for_pid 999) ]] \
    || fail "an unknown PID matched an instance"

printf 'PASS: hypr-screenshot instance lookup\n'

# --- Demo frames keep their own display time --------------------------------
# Read by animation_frame_args in the sourced script.
# shellcheck disable=SC2034
FRAME_FILES=("$TEST_DIR/frame 0.png" "$TEST_DIR/frame-1.png")
# shellcheck disable=SC2034
FRAME_DELAYS=(250 25)
mapfile -d '' frame_args < <(animation_frame_args)
expected_args=(-delay 250 "$TEST_DIR/frame 0.png" -delay 25 "$TEST_DIR/frame-1.png")
[[ ${frame_args[*]} == "${expected_args[*]}" && ${#frame_args[@]} -eq 6 ]] \
    || fail "unexpected animation arguments: ${frame_args[*]}"

printf 'PASS: hypr-screenshot animation frame timing\n'

# --- A failed encode leaves the previous image untouched -------------------
mkdir -p "$TEST_DIR/dist"
OUT="$TEST_DIR/dist/hyprland.webp"
printf 'previous image' >"$OUT"

failing_encoder()
{
    printf 'partial' >"$1"
    return 1
}
empty_encoder()
{
    : >"$1"
}
writing_encoder()
{
    printf 'new image' >"$1"
}

write_atomically "$OUT" failing_encoder && fail "a failed encode reported success"
write_atomically "$OUT" empty_encoder && fail "an empty encode reported success"
[[ $(<"$OUT") == "previous image" ]] \
    || fail "a failed encode replaced the previous image"
leftovers=$(find "$TEST_DIR/dist" -name '.hypr-screenshot.*')
[[ -z $leftovers ]] || fail "a failed encode left a temporary file: $leftovers"
write_atomically "$OUT" writing_encoder || fail "a successful encode reported failure"
[[ $(<"$OUT") == "new image" ]] || fail "a successful encode did not replace the image"

printf 'PASS: hypr-screenshot atomic output\n'
