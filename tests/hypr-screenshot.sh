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
# CI runs as root, which the sandbox passwd legitimately names.
if [[ $real_user != root ]] && grep -qF -- "$real_user" "$WORK_DIR/passwd" "$WORK_DIR/group"; then
    fail "the sandbox identity files name the real user"
fi

home="$WORK_DIR/home"
(build_demo_home "$home") || fail "the demo home could not be built"
for rendered in .zshrc .config/hypr/hyprlock.conf .gtkrc-2.0 .config/gtk-3.0/settings.ini \
    .config/hypr/hyprtoolkit.conf .config/mako/config .config/waybar/config \
    .config/hypr/hosts/settings.lua; do
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
jq -e '(.["modules-right"] | index("clock") == null and index("tray") != null
        and all(startswith("temperature#") | not))
    and (.include | all(endswith("/temperature.json") | not))' \
    "$home/.config/waybar/config" >/dev/null \
    || fail "the demo Waybar config is not the generic one of the role defaults"
[[ -L $home/.config/gtk-3.0/gtk.css ]] || fail "the demo home lost the GTK 3 stylesheet"
# wlogout reads its layout and its style, which imports the Waybar colors.
for file in layout style.css; do
    [[ -L $home/.config/wlogout/$file ]] || fail "the demo home lacks wlogout/$file"
done
[[ -L $home/.config/waybar/style.css ]] \
    || fail "the demo wlogout style cannot import the Waybar colors"

# --- The logout menu is the one of the $mod + Delete binding ---------------
menu=$(logout_menu_command) || fail "the logout menu command could not be read"
grep -qF -- "|| $menu\"," "$HYPR_CONFIG_DIR/config.lua" \
    || fail "the demo logout menu differs from utils.logout: $menu"
printf '    logout = "pkill -x wlogout || wlogout; rm -rf ~",\n' >"$TEST_DIR/config.lua"
(HYPR_CONFIG_DIR=$TEST_DIR logout_menu_command) >/dev/null 2>&1 \
    && fail "a logout command with shell syntax was accepted"
# The demo follows the theme of the role defaults, whatever it is.
theme=$(sed -n 's/^dotfiles_icon_theme: *//p' "$ROOT_DIR/ansible/roles/dotfiles/defaults/main.yml")
grep -qx "gtk-icon-theme-name=\"$theme\"" "$home/.gtkrc-2.0" \
    || fail "the demo GTK 2 settings do not use the role icon theme $theme"
grep -qx "gtk-icon-theme-name=$theme" "$home/.config/gtk-3.0/settings.ini" \
    || fail "the demo GTK 3 settings do not use the role icon theme $theme"
grep -qx "icon_theme = $theme" "$home/.config/hypr/hyprtoolkit.conf" \
    || fail "the demo hyprtoolkit config does not use the role icon theme $theme"
grep -qx "icon-path=/usr/share/icons/$theme:/usr/share/icons/${theme%-Dark}" \
    "$home/.config/mako/config" \
    || fail "the demo Mako config does not search the role icon theme $theme"
grep -rqF -- "/home/$real_user" "$home" && fail "the demo home mentions the real home"

printf 'PASS: hypr-screenshot demo home\n'

# --- The nested compositor reads a rendered hyprtoolkit.conf ----------------
hypr_home="$WORK_DIR/hypr-home"
(build_hypr_home "$hypr_home") || fail "the compositor home could not be built"
toolkit="$hypr_home/.config/hypr/hyprtoolkit.conf"
[[ -f $toolkit && ! -L $toolkit ]] || fail "hyprtoolkit.conf was not rendered for the compositor"
grep -qx "icon_theme = $theme" "$toolkit" \
    || fail "the compositor hyprtoolkit config does not use the role icon theme $theme"

printf 'PASS: hypr-screenshot compositor home\n'

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
if [[ $real_user != root && " ${client_env[*]} " == *"$real_user"* ]]; then
    fail "the client environment names the real user"
fi

printf 'PASS: hypr-screenshot client environment\n'

# --- The entry config skips startup hooks and loads the repo modules -------
lua_bin=""
for candidate in lua lua5.4 lua5.3 luajit; do
    if command -v "$candidate" >/dev/null 2>&1; then
        lua_bin=$candidate
        break
    fi
done
if [[ -n $lua_bin ]]; then
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

    result=$("$lua_bin" - "$TEST_DIR/entry.lua" <<'EOF'
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

# --- A window move is captured only once the layout has applied it ---------
# The fake instance logs each dispatch; when MOVE_APPLIES is set the focused
# window jumps between x=0 and x=960, and the dispatch is rejected for "u".
cat >"$TEST_DIR/bin/hyprctl" <<'EOF'
#!/bin/sh
shift 2 # -i SIG
case "$1" in
    activewindow) printf '{"at":[%s,40]}\n' "$(cat "$FAKE_STATE/x")" ;;
    clients) cat "$FAKE_STATE/clients" ;;
    dispatch)
        printf '%s\n' "$2" >>"$FAKE_STATE/dispatched"
        case "$2" in *'"u"'*) printf 'error\n'; exit 0 ;; esac
        if [ -n "${MOVE_APPLIES:-}" ]; then
            if [ "$(cat "$FAKE_STATE/x")" = 0 ]; then x=960; else x=0; fi
            printf '%s\n' "$x" >"$FAKE_STATE/x"
        fi
        printf 'ok\n'
        ;;
esac
EOF
cat >"$TEST_DIR/bin/grim" <<'EOF'
#!/bin/sh
: >"$3"
EOF
chmod +x "$TEST_DIR/bin/hyprctl" "$TEST_DIR/bin/grim"

move_case()
{
    rm -rf "$TEST_DIR/state" && mkdir -p "$TEST_DIR/state"
    printf '0\n' >"$TEST_DIR/state/x"
    # The settings below are read by the sourced functions.
    # shellcheck disable=SC2030,SC2031,SC2034
    (
        export FAKE_STATE="$TEST_DIR/state" MOVE_APPLIES="$2"
        SIG=showcase WORK_DIR="$TEST_DIR/state" STARTUP_TIMEOUT=1 POLL_INTERVAL=0.05 WINDOW_DELAY=0
        FRAME_FILES=() FRAME_DELAYS=()
        move_window HEADLESS-2 "$1" >/dev/null 2>&1 || exit 1
        printf '%s %s\n' "${#FRAME_FILES[@]}" "${FRAME_DELAYS[0]}"
    )
}

[[ $(move_case l 1) == "1 $DELAY_MOVE" ]] \
    || fail "an applied move was not captured as one frame"
grep -qxF 'hl.dsp.window.move({ direction = "l" })' "$TEST_DIR/state/dispatched" \
    || fail "unexpected move dispatch: $(cat "$TEST_DIR/state/dispatched")"
move_case l "" >/dev/null && fail "a move the layout never applied was captured"
move_case u 1 >/dev/null && fail "a rejected move was captured"

# A still-only run (empty DEMO_OUT) takes no demo frame.
frame_case()
{
    # shellcheck disable=SC2030,SC2031,SC2034
    (
        DEMO_OUT="$1" WORK_DIR="$TEST_DIR/state" WINDOW_DELAY=0
        FRAME_FILES=() FRAME_DELAYS=()
        demo_frame HEADLESS-2 "$DELAY_EMPTY" || exit 1
        printf '%s\n' "${#FRAME_FILES[@]}"
    )
}
[[ $(frame_case "$TEST_DIR/demo.webp") == 1 ]] || fail "a demo run did not capture its frame"
[[ $(frame_case "") == 0 ]] || fail "a still-only run captured a demo frame"

# demo_move goes towards the other half of the screen and back, and leaves a
# lone window alone. START_X is where the terminal opened, CLIENTS the mapped
# client list; prints the dispatched directions and the frame count.
demo_move_case()
{
    rm -rf "$TEST_DIR/state" && mkdir -p "$TEST_DIR/state"
    printf '%s\n' "$1" >"$TEST_DIR/state/x"
    printf '%s\n' "$2" >"$TEST_DIR/state/clients"
    : >"$TEST_DIR/state/dispatched"
    # shellcheck disable=SC2030,SC2031,SC2034
    (
        export FAKE_STATE="$TEST_DIR/state" MOVE_APPLIES=1
        SIG=showcase WORK_DIR="$TEST_DIR/state" STARTUP_TIMEOUT=1 POLL_INTERVAL=0.05
        WINDOW_DELAY=0 RES=1920x1080 DEMO_OUT="$TEST_DIR/demo.webp"
        FRAME_FILES=() FRAME_DELAYS=()
        demo_move HEADLESS-2 >/dev/null 2>&1 || exit 1
        dirs="$(sed -n 's/.*direction = "\(.\)".*/\1/p' "$FAKE_STATE/dispatched" | tr -d '\n')"
        printf '%s %s\n' "${dirs:--}" "${#FRAME_FILES[@]}"
    )
}
two='[{"mapped":true},{"mapped":true}]'
[[ $(demo_move_case 0 "$two") == "rl 2" ]] \
    || fail "a window on the left half did not go right and back: $(demo_move_case 0 "$two")"
[[ $(demo_move_case 1200 "$two") == "lr 2" ]] \
    || fail "a window on the right half did not go left and back: $(demo_move_case 1200 "$two")"
[[ $(demo_move_case 0 '[{"mapped":true},{"mapped":false}]') == "- 0" ]] \
    || fail "a lone mapped window was moved"

printf 'PASS: hypr-screenshot window moves\n'

# --- Fastfetch shows no detail of the real machine --------------------------
ff_src="$ROOT_DIR/ansible/roles/dotfiles/files/home/.config/fastfetch/config.jsonc"
ff_out="$TEST_DIR/fastfetch.jsonc"
(render_fastfetch_config "$ff_src" "$ff_out") 2>/dev/null \
    || fail "the repository Fastfetch config was rejected"
# Every module of the rendered config: bare names and "type" values.
ff_modules=$(sed -nE -e 's/^[[:space:]]*"([a-z]+)",?[[:space:]]*$/\1/p' \
    -e 's/.*"type"[[:space:]]*:[[:space:]]*"([a-z]+)".*/\1/p' "$ff_out")
for leak in kernel packages uptime host cpu loadavg gpu memory disk; do
    grep -qx -- "$leak" <<<"$ff_modules" && fail "Fastfetch module '$leak' reaches the picture"
done
grep -q '"type": "top"' "$ff_out" && fail "a Fastfetch top module measures real processes"
[[ $(grep -c '"type": "custom"' "$ff_out") == 11 ]] \
    || fail "the hidden modules did not keep their place in the layout"
grep -qF '{ "type": "custom", "key": "CPU", "format": "Intel Pentium MMX @ 233 MHz" },' "$ff_out" \
    || fail "the CPU line does not show the stand-in value"
grep -qF '{ "type": "custom", "key": "Disk", "format": "1.2 GiB / 3.2 GiB (37%) - ext4" }' "$ff_out" \
    || fail "the Disk line does not show the stand-in value"
grep -q '"format": "hidden"' "$ff_out" && fail "a Fastfetch module shows a placeholder instead of a made-up value"
# shellcheck disable=SC2034 # read by render_fastfetch_config
(FASTFETCH_HIDDEN=(disk:Disk); render_fastfetch_config "$ff_src" "$TEST_DIR/ff.out") 2>/dev/null \
    && fail "a Fastfetch module without a stand-in value was accepted"
grep -qF '{ "type": "custom", "key": "RAM process", "format": "alacritty (31) - MEM 24.0 MiB" },' "$ff_out" \
    || fail "the RAM process line does not show the stand-in value"
grep -qx os <<<"$ff_modules" || fail "a session module was dropped"
# Everything before the modules is copied as it is, the logo object included.
[[ $(sed -n '1,/"modules"/p' "$ff_out") == $(sed -n '1,/"modules"/p' "$ff_src") ]] \
    || fail "the Fastfetch logo settings were changed"
jq -e . >/dev/null 2>&1 < <(sed -E 's#^[[:space:]]*//.*##' "$ff_out" | tr -d '\n' | sed -E 's/,[[:space:]]*([]}])/\1/g') \
    || fail "the rendered Fastfetch config is not valid JSONC"

# A module the script does not know is refused, as a bare name or an object.
printf '{ "modules": [\n  "os",\n  "battery",\n] }\n' >"$TEST_DIR/ff-bare.jsonc"
(render_fastfetch_config "$TEST_DIR/ff-bare.jsonc" "$TEST_DIR/ff.out") 2>/dev/null \
    && fail "an unknown bare Fastfetch module was accepted"
printf '{ "modules": [\n  { "type": "cpu", "key": "x" },\n] }\n' >"$TEST_DIR/ff-object.jsonc"
(render_fastfetch_config "$TEST_DIR/ff-object.jsonc" "$TEST_DIR/ff.out") 2>/dev/null \
    && fail "a Fastfetch module in object form bypassed the filter"

# A multi-line module other than "top", or a "top" sorted on something else.
printf '{ "modules": [\n  {\n    "type": "gpu",\n    "key": "x",\n  },\n] }\n' >"$TEST_DIR/ff-multi.jsonc"
(render_fastfetch_config "$TEST_DIR/ff-multi.jsonc" "$TEST_DIR/ff.out") 2>/dev/null \
    && fail "a multi-line Fastfetch module bypassed the filter"
printf '{ "modules": [\n  {\n    "type": "top",\n    "key": "x",\n    "sort": "pid",\n  },\n] }\n' >"$TEST_DIR/ff-top.jsonc"
(render_fastfetch_config "$TEST_DIR/ff-top.jsonc" "$TEST_DIR/ff.out") 2>/dev/null \
    && fail "a top module without a stand-in value was accepted"

# Modules hidden in another layout are refused instead of copied as they are.
printf '{ "modules": ["os", "cpu"] }\n' >"$TEST_DIR/ff-inline.jsonc"
(render_fastfetch_config "$TEST_DIR/ff-inline.jsonc" "$TEST_DIR/ff.out") 2>/dev/null \
    && fail "an inline Fastfetch module list was copied unfiltered"
printf '{ "modules": [\n  "os", "cpu",\n] }\n' >"$TEST_DIR/ff-pair.jsonc"
(render_fastfetch_config "$TEST_DIR/ff-pair.jsonc" "$TEST_DIR/ff.out") 2>/dev/null \
    && fail "two Fastfetch modules on one line were copied unfiltered"

# Keys outside the module list, comments and nested arrays are not modules.
printf '{\n  "logo": {\n    "type": "small",\n  },\n  // "gpu",\n  "modules": [\n    // "gpu",\n    {\n      "type": "top",\n      "key": "a",\n      "sort": "cpu",\n      "showTypes": [\n        "cpu"\n      ],\n    },\n    {\n      "type": "top",\n      "key": "b",\n      "sort": "memory",\n    },\n    "os",\n  ],\n}\n' >"$TEST_DIR/ff-layout.jsonc"
(render_fastfetch_config "$TEST_DIR/ff-layout.jsonc" "$TEST_DIR/ff.out") 2>/dev/null \
    || fail "a Fastfetch config with logo type, comments or nested arrays was rejected"
grep -q '"type": "top"' "$TEST_DIR/ff.out" && fail "a top module after a nested array was not hidden"
grep -q '"type": "small"' "$TEST_DIR/ff.out" || fail "the Fastfetch logo type was changed"

printf 'PASS: hypr-screenshot Fastfetch anonymised\n'

# --- Waybar shows no live state of the real machine -------------------------
wb_out="$TEST_DIR/waybar.json"
(render_waybar_config "$wb_out") 2>/dev/null || fail "the repository Waybar config was rejected"
wb_right=$(jq -r '."modules-right"[]' "$wb_out")
for leak in custom/vpn custom/lact-profile custom/headsetcontrol; do
    grep -qx -- "$leak" <<<"$wb_right" && fail "Waybar module '$leak' reaches the picture"
done
for fixed in cpu memory pulseaudio bluetooth; do
    grep -qx -- "$fixed" <<<"$wb_right" || fail "Waybar module '$fixed' was dropped"
    # One text for every state, no placeholder left and no tooltip.
    texts=$(jq -r --arg m "$fixed" '.[$m] | to_entries[] | select(.key | startswith("format")) | .value' "$wb_out")
    [[ -n $texts && $(sort -u <<<"$texts" | wc -l) == 1 ]] \
        || fail "Waybar module '$fixed' has a text per state: $texts"
    grep -q '[{}]' <<<"$texts" && fail "Waybar module '$fixed' keeps a placeholder: $texts"
    [[ $(jq --arg m "$fixed" '.[$m].tooltip' "$wb_out") == false ]] \
        || fail "Waybar module '$fixed' keeps its tooltip"
done
# Each format key of the include is overridden, so no live variant is merged in.
wb_src="$ROOT_DIR/ansible/roles/dotfiles/files/home/.config/waybar/conf"
missing=$(jq -rs --slurpfile out "$wb_out" '
    add as $src | ["cpu", "memory", "pulseaudio", "bluetooth"][] as $m
    | $src[$m] | keys[] | select(startswith("format") and . != "format-icons")
    | select($out[0][$m][.] == null) | "\($m).\(.)"' "$wb_src"/*.json)
[[ -z $missing ]] || fail "live Waybar formats are not overridden: $missing"

# A module the script does not know is refused.
printf 'dotfiles_waybar_modules_right:\n  - cpu\n  - network\ndotfiles_waybar_includes:\n  - ~/.config/waybar/conf/system.json\n' \
    >"$TEST_DIR/waybar-defaults.yml"
(DOTFILES_DEFAULTS="$TEST_DIR/waybar-defaults.yml" render_waybar_config "$TEST_DIR/wb.out") 2>/dev/null \
    && fail "an unknown Waybar module was accepted"

printf 'PASS: hypr-screenshot Waybar anonymised\n'
