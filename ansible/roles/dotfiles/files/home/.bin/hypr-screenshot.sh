#!/usr/bin/env bash
#
# hypr-screenshot.sh - Render the desktop showcase used in the README.
#
# A throwaway Hyprland instance loads the Hyprland config of this repository on
# a virtual headless output of fixed size and opens Waybar, an editor and a
# terminal. That desktop is saved as a still WebP. The script then plays a
# short demo on it, captured frame by frame into an animated WebP: Hyprlauncher
# opens and searches for an application, Mako shows a notification, and
# Hyprlock locks the screen. Both files are written atomically, so a failed
# run never leaves a broken image behind.
#
# Nothing personal ends up in the pictures:
#   - clients run in user, mount, UTS and PID namespaces as user "demo" on
#     host "dotfiles", with an empty environment, a throwaway /home/demo built
#     from the configs of this repository, and the repository mounted
#     read-only at ~/.dotfiles; the real /home is hidden and only their own
#     processes are visible;
#   - they get a private D-Bus session bus and runtime directory, so the
#     notification and the launcher never reach the daemons of the session;
#   - Hyprland starts with an empty environment too (it only keeps the host
#     Wayland socket to open its nested window) and skips its
#     `hyprland.start` hooks, so no gsettings, polkit agent, clipboard watcher
#     or `uwsm app` unit is started;
#   - animations are disabled, the pointer is hidden and the built-in
#     wallpaper is pinned, so two runs give the same frames.
# Hyprland opens its nested output as a window on the host until the headless
# output replaces it; that is expected.
#
# Neovim reads its plugins from ~/.local/share/nvim, mounted read-only. A
# missing optional tool skips its part of the demo.
#
# Usage:
#   hypr-screenshot.sh [output.webp]
#
# Environment:
#   OUT              still image (default: $DOTFILES_REPOSITORY/dist/hyprland.webp)
#   DEMO_OUT         animated demo (default: OUT with a -demo suffix; empty: none)
#   DEMO_WIDTH       width of the animated demo in pixels (default: 1280)
#   DEMO_QUERY       text typed in Hyprlauncher, a-z and 0-9 (default: fire)
#   RES              output resolution WIDTHxHEIGHT (default: 1920x1080)
#   WEBP_QUALITY     WebP quality 0-100 (default: 80)
#   EDITOR_FILE      file opened in Neovim, relative to the repository
#                    (default: README.md)
#   WAYBAR_CONFIG    Waybar config of the repository to use (default: the one
#                    for this host, else the first config.* file)
#   SETTLE           seconds to wait after the windows map (default: 2)

set -euo pipefail

STARTUP_TIMEOUT=15 # seconds to wait for the instance, windows and layers
POLL_INTERVAL=0.25
# Nothing reports when a client has redrawn after a key press or when Hyprlock
# has drawn its widgets, so these steps wait a fixed time.
REDRAW_DELAY=0.3
LOCK_DELAY=2.5
# Unix socket paths are limited to 107 bytes.
SOCKET_PATH_MAX=107

# Identity shown in the pictures.
DEMO_USER=demo
DEMO_HOST=dotfiles
DEMO_HOME=/home/$DEMO_USER
SANDBOX_PATH=/usr/local/sbin:/usr/local/bin:/usr/bin:/bin

# Frame display times in the demo, in hundredths of a second.
DELAY_DESKTOP=250
DELAY_LAUNCHER_OPEN=50
DELAY_KEYSTROKE=25
DELAY_SEARCH_RESULT=150
DELAY_NOTIFICATION=250
DELAY_LOCK=250

REPO="${DOTFILES_REPOSITORY:-${HOME}/.dotfiles}"
OUT="${1:-${OUT:-$REPO/dist/hyprland.webp}}"
DEMO_OUT="${DEMO_OUT-${OUT%.*}-demo.webp}"
DEMO_WIDTH="${DEMO_WIDTH:-1280}"
DEMO_QUERY="${DEMO_QUERY:-fire}"
RES="${RES:-1920x1080}"
WEBP_QUALITY="${WEBP_QUALITY:-80}"
EDITOR_FILE="${EDITOR_FILE:-README.md}"
WAYBAR_CONFIG="${WAYBAR_CONFIG:-}"
SETTLE="${SETTLE:-2}"
DOTFILES_HOME="$REPO/ansible/roles/dotfiles/files/home"
DOTFILES_TEMPLATES="$REPO/ansible/roles/dotfiles/templates/home"
HYPR_CONFIG_DIR="$DOTFILES_HOME/.config/hypr"
TERM_EMU=alacritty

HYPR_PID=""
SIG=""
WORK_DIR=""
DBUS_PID=""
SANDBOX_PID=""
NESTED_WAYLAND=""
FRAME_FILES=()
FRAME_DELAYS=()

die()
{
    printf 'hypr-screenshot: %s\n' "$*" >&2
    exit 1
}

log()
{
    printf 'hypr-screenshot: %s\n' "$*"
}

has()
{
    command -v "$1" >/dev/null 2>&1
}

# Check user input before anything is started.
validate_settings()
{
    [[ $RES =~ ^[1-9][0-9]*x[1-9][0-9]*$ ]] \
        || die "RES must look like 1920x1080, got '$RES'"
    if [[ ! $WEBP_QUALITY =~ ^[0-9]+$ ]] || ((10#$WEBP_QUALITY > 100)); then
        die "WEBP_QUALITY must be an integer from 0 to 100, got '$WEBP_QUALITY'"
    fi
    [[ $SETTLE =~ ^[0-9]+([.][0-9]+)?$ ]] \
        || die "SETTLE must be a number of seconds, got '$SETTLE'"
    [[ $DEMO_WIDTH =~ ^[1-9][0-9]*$ ]] \
        || die "DEMO_WIDTH must be a positive integer, got '$DEMO_WIDTH'"
    # Each character becomes a key name for Hyprland's send_shortcut.
    [[ $DEMO_QUERY =~ ^[a-z0-9]+$ ]] \
        || die "DEMO_QUERY may only hold a-z and 0-9, got '$DEMO_QUERY'"
    [[ $EDITOR_FILE != /* && $EDITOR_FILE != *..* && -f $REPO/$EDITOR_FILE ]] \
        || die "EDITOR_FILE must name a file inside the repository, got '$EDITOR_FILE'"
    [[ -f $HYPR_CONFIG_DIR/hyprland.lua ]] \
        || die "no hyprland.lua in '$HYPR_CONFIG_DIR'"
    # The directory is embedded in a Lua long string.
    [[ $HYPR_CONFIG_DIR != *']==]'* ]] \
        || die "the repository path cannot contain ']==]'"
}

require_tools()
{
    local bin
    for bin in Hyprland hyprctl grim jq dbus-daemon unshare hostname "$TERM_EMU"; do
        has "$bin" || die "required tool '$bin' not found in PATH"
    done
    unshare --user --map-root-user true 2>/dev/null \
        || die "unprivileged user namespaces are disabled; the capture needs them"
    # Only ImageMagick writes animated WebP with exact frame times here.
    if [[ -n $DEMO_OUT ]] && ! has magick; then
        die "the animated demo needs ImageMagick ('magick'); set DEMO_OUT= to skip it"
    fi
}

# Print the first available WebP encoder. cwebp gives the best size/quality.
pick_encoder()
{
    local bin
    for bin in cwebp magick ffmpeg; do
        if has "$bin"; then
            printf '%s\n' "$bin"
            return 0
        fi
    done
    return 1
}

# encode_webp ENCODER SRC_PNG DST_WEBP
encode_webp()
{
    local encoder="$1" src="$2" dst="$3"
    case "$encoder" in
        cwebp) cwebp -quiet -q "$WEBP_QUALITY" -m 6 "$src" -o "$dst" ;;
        magick) magick "$src" -strip -quality "$WEBP_QUALITY" -define webp:method=6 "$dst" ;;
        ffmpeg) ffmpeg -nostdin -loglevel error -y -i "$src" -c:v libwebp \
            -compression_level 6 -quality "$WEBP_QUALITY" "$dst" ;;
        *) return 1 ;;
    esac
}

# Print the ImageMagick arguments for the recorded frames: `-delay D file`...
animation_frame_args()
{
    local i
    for i in "${!FRAME_FILES[@]}"; do
        printf '%s\0' -delay "${FRAME_DELAYS[$i]}" "${FRAME_FILES[$i]}"
    done
}

# encode_animation DST_WEBP
encode_animation()
{
    local frames=()
    mapfile -d '' frames < <(animation_frame_args)
    magick "${frames[@]}" -loop 0 -resize "${DEMO_WIDTH}x" -strip \
        -quality "$WEBP_QUALITY" -define webp:method=6 "$1"
}

# write_atomically DST COMMAND... - run COMMAND with a temporary file next to
# DST as its last argument, then move it over DST only if it is not empty.
write_atomically()
{
    local dst="$1" tmp
    shift
    mkdir -p -- "$(dirname -- "$dst")"
    tmp="$(mktemp --tmpdir="$(dirname -- "$dst")" .hypr-screenshot.XXXXXX.webp)"
    if ! "$@" "$tmp" || [[ ! -s $tmp ]]; then
        rm -f -- "$tmp"
        return 1
    fi
    chmod 0644 "$tmp"
    mv -f -- "$tmp" "$dst"
}

# Write the Lua entry point that loads HYPR_CONFIG_DIR without its startup
# hooks and with animations disabled. write_entry_config DIR DEST
write_entry_config()
{
    local dir="$1" dest="$2"
    cat >"$dest" <<EOF
-- Generated by hypr-screenshot.sh. Loads the dotfiles config for a capture.
local hl = rawget(_G, "hl")
local config_dir = [==[$dir]==]
package.path = config_dir .. "/?.lua;" .. config_dir .. "/?/init.lua;" .. package.path

-- Startup hooks touch the live session (gsettings, polkit, cliphist, uwsm).
local on = hl.on
hl.on = function(event, ...)
  if event ~= "hyprland.start" then
    return on(event, ...)
  end
end
dofile(config_dir .. "/hyprland.lua")
hl.on = on

-- Fixed visuals: no animation mid-capture, no stray pointer, and the same
-- built-in wallpaper every run instead of a random one.
hl.config({
  animations = { enabled = false },
  cursor = { invisible = true },
  misc = { force_default_wallpaper = 2 },
})
EOF
}

# render_template SRC DST NAME=VALUE... - replace each `{{ NAME }}` of an
# Ansible template, and fail if any expression is left.
render_template()
{
    local src="$1" dst="$2" pair text
    shift 2
    text="$(<"$src")"
    for pair in "$@"; do
        text="${text//"{{ ${pair%%=*} }}"/${pair#*=}}"
    done
    [[ $text != *'{{'* && $text != *'{%'* ]] \
        || die "unhandled template expression in $src"
    printf '%s\n' "$text" >"$dst"
}

# link_tree SRC DST - make DST a directory of symlinks to the entries of SRC,
# so files can be added to DST without touching SRC.
link_tree()
{
    local src="$1" dst="$2" entry
    mkdir -p -- "$dst"
    for entry in "$src"/* "$src"/.[!.]*; do
        [[ -e $entry ]] || continue
        ln -s -- "$(sandbox_path "$entry")" "$dst/${entry##*/}"
    done
}

# Print where a repository path is seen from inside the sandbox.
sandbox_path()
{
    printf '%s\n' "$DEMO_HOME/.dotfiles/${1#"$REPO"/}"
}

# Print the Waybar config file of the repository to use.
pick_waybar_config()
{
    local dir="$DOTFILES_HOME/.config/waybar" candidate
    if [[ -n $WAYBAR_CONFIG ]]; then
        [[ -f $dir/$WAYBAR_CONFIG ]] || die "no Waybar config '$WAYBAR_CONFIG' in $dir"
        printf '%s\n' "$dir/$WAYBAR_CONFIG"
        return 0
    fi
    candidate="$dir/config.$(</proc/sys/kernel/hostname)"
    if [[ ! -f $candidate ]]; then
        candidate="$(find "$dir" -maxdepth 1 -name 'config.*' -type f | sort | head -n 1)"
    fi
    [[ -n $candidate ]] || die "no Waybar config.* file in $dir"
    printf '%s\n' "$candidate"
}

# build_demo_home DIR - the home directory of the demo user, made of links to
# the repository as mounted in the sandbox and of rendered templates.
build_demo_home()
{
    local home="$1" name
    mkdir -p -- "$home/.config" "$home/.local/share/nvim" "$home/.local/share/dotfiles" \
        "$home/.dotfiles"

    for name in alacritty fastfetch nvim; do
        ln -s -- "$(sandbox_path "$DOTFILES_HOME/.config/$name")" "$home/.config/$name"
    done
    for name in .bin .zshenv; do
        ln -s -- "$(sandbox_path "$DOTFILES_HOME/$name")" "$home/$name"
    done
    # Same place as dotfiles_zsh_link_dest in the role defaults.
    ln -s -- "$(sandbox_path "$DOTFILES_HOME/zsh")" "$home/.local/share/dotfiles/zsh"

    render_template "$DOTFILES_TEMPLATES/.zshrc.j2" "$home/.zshrc" \
        "ansible_managed=Generated by hypr-screenshot.sh" \
        "dotfiles_zsh_home=$DEMO_HOME/.local/share/dotfiles/zsh"

    mkdir -p -- "$home/.config/gtk-3.0" "$home/.config/mako"
    render_template "$DOTFILES_TEMPLATES/.gtkrc-2.0.j2" "$home/.gtkrc-2.0" \
        "dotfiles_icon_theme=Papirus-Dark"
    render_template "$DOTFILES_TEMPLATES/.config/gtk-3.0/settings.ini.j2" \
        "$home/.config/gtk-3.0/settings.ini" "dotfiles_icon_theme=Papirus-Dark"
    render_template "$DOTFILES_TEMPLATES/.config/mako/config.j2" \
        "$home/.config/mako/config" "dotfiles_icon_theme=Papirus-Dark" \
        "dotfiles_icon_theme_parent=Papirus"

    link_tree "$HYPR_CONFIG_DIR" "$home/.config/hypr"
    render_template "$DOTFILES_TEMPLATES/.config/hypr/hyprtoolkit.conf.j2" \
        "$home/.config/hypr/hyprtoolkit.conf" \
        "dotfiles_icon_theme=Papirus-Dark" "dotfiles_icon_theme_parent=Papirus"
    render_template "$DOTFILES_TEMPLATES/.config/hypr/hyprlock.conf.j2" \
        "$home/.config/hypr/hyprlock.conf" "dotfiles_repository=$DEMO_HOME/.dotfiles"

    link_tree "$DOTFILES_HOME/.config/waybar" "$home/.config/waybar"
    ln -s -- "$(sandbox_path "$(pick_waybar_config)")" "$home/.config/waybar/config"
}

# write_identity DIR - passwd and group files naming only root and the demo user.
write_identity()
{
    local shell=/bin/bash
    [[ -x /usr/bin/zsh ]] && shell=/usr/bin/zsh
    printf 'root:x:0:0::/root:/bin/sh\n%s:x:%d:%d::%s:%s\n' \
        "$DEMO_USER" "$UID" "$(id -g)" "$DEMO_HOME" "$shell" >"$1/passwd"
    printf 'root:x:0:\n%s:x:%d:\n' "$DEMO_USER" "$(id -g)" >"$1/group"
}

# Session bus config without service directories: nothing is started on
# demand (portals, for one), so no daemon outlives the instance.
write_dbus_config()
{
    cat >"$1" <<'EOF'
<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <type>session</type>
  <listen>unix:tmpdir=/tmp</listen>
  <policy context="default">
    <allow send_destination="*" eavesdrop="true"/>
    <allow eavesdrop="true"/>
    <allow own="*"/>
  </policy>
</busconfig>
EOF
}

# The sandbox runs as root of a new user namespace to set the hostname and
# mounts, then drops to the demo user and runs every command read from a FIFO.
write_sandbox_scripts()
{
    cat >"$WORK_DIR/sandbox-init.sh" <<'EOF'
set -eu
work="$1" repo="$2" nvim_data="$3" host="$4" home="$5" uid="$6" gid="$7"
shift 7
hostname "$host"
mount --bind "$work/passwd" /etc/passwd
mount --bind "$work/group" /etc/group
# Stage the sources before /home, which may hold them, is covered.
mkdir -p "$work/stage/repo" "$work/stage/nvim"
mount --bind "$repo" "$work/stage/repo"
[ -z "$nvim_data" ] || mount --bind "$nvim_data" "$work/stage/nvim"
mount -t tmpfs -o mode=0755 tmpfs /home
mkdir "$home"
mount --bind "$work/home" "$home"
mount --bind "$work/stage/repo" "$home/.dotfiles"
mount -o remount,bind,ro "$home/.dotfiles"
if [ -n "$nvim_data" ]; then
    mount --bind "$work/stage/nvim" "$home/.local/share/nvim"
    mount -o remount,bind,ro "$home/.local/share/nvim"
fi
exec unshare --user --map-user="$uid" --map-group="$gid" -- \
    env -i "$@" bash "$work/sandbox-run.sh" "$work/clients.fifo" "$work/sandbox.ready"
EOF
    cat >"$WORK_DIR/sandbox-run.sh" <<'EOF'
cd "$HOME/.dotfiles" || exit 1
: >"$2"
while IFS= read -r command; do
    bash -c "$command" </dev/null >/dev/null 2>&1 &
done <"$1"
wait
EOF
}

# Print the environment of the clients, the only variables they receive.
sandbox_env()
{
    printf '%s\n' \
        "HOME=$DEMO_HOME" \
        "USER=$DEMO_USER" \
        "LOGNAME=$DEMO_USER" \
        "SHELL=$(awk -F: -v u="$DEMO_USER" '$1 == u { print $7 }' "$WORK_DIR/passwd")" \
        "PATH=$SANDBOX_PATH" \
        "LANG=C.UTF-8" \
        "XDG_RUNTIME_DIR=$WORK_DIR" \
        "XDG_SESSION_TYPE=wayland" \
        "XDG_CURRENT_DESKTOP=Hyprland" \
        "WAYLAND_DISPLAY=$NESTED_WAYLAND" \
        "HYPRLAND_INSTANCE_SIGNATURE=$SIG" \
        "DBUS_SESSION_BUS_ADDRESS=$1"
}

# Print the instance signature owned by PID, from `hyprctl instances -j`.
instance_for_pid()
{
    hyprctl instances -j 2>/dev/null \
        | jq -r --argjson pid "$1" '.[] | select(.pid == $pid) | .instance' 2>/dev/null
}

# hctl ARGS... - hyprctl bound to the showcase instance.
hctl()
{
    hyprctl -i "$SIG" "$@"
}

monitor_names()
{
    hctl monitors -j | jq -r '.[].name'
}

client_count_is()
{
    (($(hctl clients -j | jq '[.[] | select(.mapped)] | length') >= $1))
}

# layer_mapped NAMESPACE - true when a layer surface of NAMESPACE is shown.
layer_mapped()
{
    hctl layers -j \
        | jq -e --arg ns "$1" '[.. | objects | select(.namespace? == $ns)] | length > 0' >/dev/null
}

layer_gone()
{
    ! layer_mapped "$1"
}

# wait_until DESCRIPTION COMMAND... - poll COMMAND until it succeeds.
wait_until()
{
    local what="$1" deadline
    shift
    deadline=$((SECONDS + STARTUP_TIMEOUT))
    until "$@"; do
        ((SECONDS < deadline)) || die "timed out waiting for $what"
        sleep "$POLL_INTERVAL"
    done
}

# send_key KEY - type KEY into the focused surface of the instance.
send_key()
{
    [[ $(hctl dispatch "hl.dsp.send_shortcut({ mods = \"\", key = \"$1\" })") == ok ]] \
        || die "Hyprland rejected key '$1'"
}

# Runs as the EXIT trap under errexit, so no step may fail.
cleanup()
{
    if [[ -n $SANDBOX_PID ]]; then
        # unshare ignores SIGTERM while it waits, and the namespace's PID 1
        # has no handlers; with --kill-child, killing unshare ends them all.
        kill -KILL "$SANDBOX_PID" 2>/dev/null || true
        wait "$SANDBOX_PID" 2>/dev/null || true
    fi
    if [[ -n $DBUS_PID ]]; then
        kill "$DBUS_PID" 2>/dev/null || true
    fi
    if [[ -n $HYPR_PID ]]; then
        if [[ -n $SIG ]]; then
            hctl dispatch 'hl.dsp.exit()' >/dev/null 2>&1 || true
        fi
        local deadline=$((SECONDS + 5))
        while kill -0 "$HYPR_PID" 2>/dev/null && ((SECONDS < deadline)); do
            sleep "$POLL_INTERVAL"
        done
        # setsid made Hyprland a group leader: this also stops Xwayland.
        kill -TERM -- "-$HYPR_PID" 2>/dev/null || true
        wait "$HYPR_PID" 2>/dev/null || true
    fi
    # The sandbox mounts lived in its own namespace: these are plain files here.
    if [[ -n $WORK_DIR ]]; then
        rm -rf -- "$WORK_DIR" || true
    fi
    return 0
}

start_instance()
{
    local host_runtime="${XDG_RUNTIME_DIR:-/run/user/$UID}"
    write_entry_config "$HYPR_CONFIG_DIR" "$WORK_DIR/showcase.lua"
    mkdir -p -- "$WORK_DIR/hypr-home/.config/hypr"
    ln -s -- "$HYPR_CONFIG_DIR/hyprtoolkit.conf" "$WORK_DIR/hypr-home/.config/hypr/hyprtoolkit.conf"

    # The host Wayland socket is the one variable kept: without it Hyprland
    # would try to drive the GPU and seat instead of nesting.
    env -i PATH="$SANDBOX_PATH" HOME="$WORK_DIR/hypr-home" LANG=C.UTF-8 \
        XDG_RUNTIME_DIR="$host_runtime" WAYLAND_DISPLAY="${WAYLAND_DISPLAY:?not in a Wayland session}" \
        HYPRLAND_NO_RT=1 WLR_LIBINPUT_NO_DEVICES=1 \
        setsid Hyprland --config "$WORK_DIR/showcase.lua" >"$WORK_DIR/hyprland.log" 2>&1 &
    HYPR_PID=$!

    local deadline=$((SECONDS + STARTUP_TIMEOUT))
    until SIG="$(instance_for_pid "$HYPR_PID")" && [[ -n $SIG ]]; do
        if ! kill -0 "$HYPR_PID" 2>/dev/null || ((SECONDS >= deadline)); then
            cat "$WORK_DIR/hyprland.log" >&2
            die "the showcase Hyprland instance did not start"
        fi
        sleep "$POLL_INTERVAL"
    done

    local wl_socket
    wl_socket="$(hyprctl instances -j | jq -r --arg sig "$SIG" '.[] | select(.instance == $sig) | .wl_socket')"
    [[ -n $wl_socket ]] || die "no Wayland socket for instance $SIG"
    NESTED_WAYLAND="$host_runtime/$wl_socket"
    log "instance $SIG"
}

# Start the private D-Bus bus and the namespaced client runner. Clients see a
# runtime directory that only exposes this instance, so Hyprlauncher's IPC
# socket and Waybar's Hyprland module stay inside it.
start_sandbox()
{
    local host_runtime="${XDG_RUNTIME_DIR:-/run/user/$UID}" socket_path nvim_data=""
    socket_path="$WORK_DIR/hypr/$SIG/.socket2.sock"
    ((${#socket_path} <= SOCKET_PATH_MAX)) \
        || die "work directory path too long for Unix sockets: $WORK_DIR"
    mkdir -p -- "$WORK_DIR/hypr"
    ln -s -- "$host_runtime/hypr/$SIG" "$WORK_DIR/hypr/$SIG"

    local address
    write_dbus_config "$WORK_DIR/dbus.conf"
    address="$(env -i PATH="$SANDBOX_PATH" dbus-daemon --config-file="$WORK_DIR/dbus.conf" \
        --fork --nopidfile --print-address=1 --print-pid=3 3>"$WORK_DIR/dbus.pid")" \
        || die "could not start a private D-Bus session bus"
    DBUS_PID="$(<"$WORK_DIR/dbus.pid")"

    write_identity "$WORK_DIR"
    build_demo_home "$WORK_DIR/home"
    write_sandbox_scripts
    [[ -d $HOME/.local/share/nvim ]] && nvim_data="$HOME/.local/share/nvim"
    mkfifo "$WORK_DIR/clients.fifo"

    local env_vars=()
    mapfile -t env_vars < <(sandbox_env "$address")
    env -i PATH="$SANDBOX_PATH" \
        unshare --user --map-root-user --mount --uts --pid --fork --kill-child --mount-proc -- \
        bash "$WORK_DIR/sandbox-init.sh" "$WORK_DIR" "$REPO" "$nvim_data" \
        "$DEMO_HOST" "$DEMO_HOME" "$UID" "$(id -g)" "${env_vars[@]}" \
        >"$WORK_DIR/sandbox.log" 2>&1 &
    SANDBOX_PID=$!
    # Read-write keeps the open from blocking until the runner reads.
    exec {CLIENTS_FD}<>"$WORK_DIR/clients.fifo"

    local deadline=$((SECONDS + STARTUP_TIMEOUT))
    until [[ -e $WORK_DIR/sandbox.ready ]]; do
        if ! kill -0 "$SANDBOX_PID" 2>/dev/null || ((SECONDS >= deadline)); then
            cat "$WORK_DIR/sandbox.log" >&2
            die "the client sandbox did not start"
        fi
        sleep "$POLL_INTERVAL"
    done
}

# Replace the nested output, sized after the host window, with a headless
# output of a fixed resolution so the capture is reproducible.
use_headless_output()
{
    local before name output=""
    before="$(monitor_names)"
    hctl output create headless >/dev/null || die "could not create a headless output"

    local deadline=$((SECONDS + STARTUP_TIMEOUT))
    while [[ -z $output ]]; do
        output="$(monitor_names | grep -vxF -- "$before" | head -n 1 || true)"
        [[ -n $output ]] && break
        ((SECONDS < deadline)) || die "the headless output did not appear"
        sleep "$POLL_INTERVAL"
    done

    while read -r name; do
        [[ $name == "$output" ]] || hctl output remove "$name" >/dev/null 2>&1 || true
    done < <(monitor_names)

    hctl eval "hl.monitor({ output = \"$output\", mode = \"$RES@60\", position = \"0x0\", scale = 1 })" >/dev/null
    wait_until "$output to switch to $RES" output_has_resolution "$output"
    printf '%s\n' "$output"
}

output_has_resolution()
{
    hctl monitors -j \
        | jq -e --arg name "$1" --arg res "$RES" \
            '.[] | select(.name == $name) | "\(.width)x\(.height)" == $res' >/dev/null
}

# spawn COMMAND... - start COMMAND as the demo user, from ~/.dotfiles.
spawn()
{
    local quoted
    printf -v quoted '%q ' "$@"
    printf '%s\n' "$quoted" >&"$CLIENTS_FD"
}

populate()
{
    local windows=0

    if has waybar; then
        spawn waybar
        wait_until "Waybar" layer_mapped waybar
    fi
    # Mako only maps a surface once a notification arrives.
    has mako && spawn mako

    # One client at a time, so dwindle always splits the same way.
    if has nvim; then
        spawn "$TERM_EMU" -e nvim "$DEMO_HOME/.dotfiles/$EDITOR_FILE"
        windows=$((windows + 1))
        wait_until "the editor window" client_count_is "$windows"
    fi
    # A login-like shell: the zshrc greets with fastfetch when SHLVL is 1.
    spawn env SHLVL=0 "$TERM_EMU"
    windows=$((windows + 1))
    wait_until "the terminal window" client_count_is "$windows"

    # Drop the config-load and start-hyprland banners of Hyprland itself.
    hctl dismissnotify >/dev/null 2>&1 || true
}

# capture_frame OUTPUT DELAY - grab the output as the next demo frame.
capture_frame()
{
    local file
    file="$WORK_DIR/frame-$(printf '%02d' "${#FRAME_FILES[@]}").png"
    WAYLAND_DISPLAY="$NESTED_WAYLAND" grim -o "$1" "$file" || die "grim capture failed"
    FRAME_FILES+=("$file")
    FRAME_DELAYS+=("$2")
}

demo_launcher()
{
    local output="$1" i
    has hyprlauncher || { log "hyprlauncher not found, skipping the search"; return 0; }

    spawn hyprlauncher
    wait_until "Hyprlauncher" layer_mapped hyprlauncher
    sleep "$REDRAW_DELAY"
    capture_frame "$output" "$DELAY_LAUNCHER_OPEN"

    for ((i = 0; i < ${#DEMO_QUERY}; i++)); do
        send_key "${DEMO_QUERY:i:1}"
        sleep "$REDRAW_DELAY"
        capture_frame "$output" "$DELAY_KEYSTROKE"
    done
    FRAME_DELAYS[-1]="$DELAY_SEARCH_RESULT"

    send_key Escape
    wait_until "Hyprlauncher to close" layer_gone hyprlauncher
}

demo_notification()
{
    local output="$1"
    if ! has mako || ! has notify-send; then
        log "mako or notify-send not found, skipping the notification"
        return 0
    fi

    spawn notify-send --app-name=Steam --icon=steam "Download complete" "Your game is ready to play"
    wait_until "the notification" layer_mapped notifications
    sleep "$REDRAW_DELAY"
    capture_frame "$output" "$DELAY_NOTIFICATION"
}

demo_lock()
{
    local output="$1"
    has hyprlock || { log "hyprlock not found, skipping the lock screen"; return 0; }

    spawn hyprlock
    sleep "$LOCK_DELAY"
    capture_frame "$output" "$DELAY_LOCK"
}

main()
{
    case "${1:-}" in
        -h | --help)
            sed -n '3,/^$/{s/^# \{0,1\}//;p}' "${BASH_SOURCE[0]}"
            return 0
            ;;
    esac

    validate_settings
    require_tools
    local encoder output
    encoder="$(pick_encoder)" || die "no WebP encoder found (need cwebp, magick or ffmpeg)"

    # Short on purpose: client sockets live under it (see SOCKET_PATH_MAX).
    WORK_DIR="$(mktemp -d /tmp/hshot.XXXXXX)"
    trap cleanup EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM

    start_instance
    start_sandbox
    output="$(use_headless_output)"
    log "capturing output $output"
    populate
    sleep "$SETTLE"
    capture_frame "$output" "$DELAY_DESKTOP"

    write_atomically "$OUT" encode_webp "$encoder" "${FRAME_FILES[0]}" \
        || die "WebP encoding with '$encoder' failed"
    log "saved $RES still ($encoder, WebP q$WEBP_QUALITY) to $OUT"

    [[ -n $DEMO_OUT ]] || return 0
    demo_launcher "$output"
    demo_notification "$output"
    demo_lock "$output"
    write_atomically "$DEMO_OUT" encode_animation \
        || die "animated WebP encoding failed"
    log "saved ${#FRAME_FILES[@]}-frame demo (${DEMO_WIDTH}px wide) to $DEMO_OUT"
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
    main "$@"
fi
