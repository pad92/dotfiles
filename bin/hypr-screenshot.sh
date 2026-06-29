#!/usr/bin/env bash
#
# hypr-screenshot.sh — Render a clean showcase of this dotfiles' Hyprland
# configuration in an isolated, nested Hyprland instance and capture it with
# grim. Nothing from the live session leaks in: a fresh compositor is spawned,
# loads ~/.config/hypr (this repo), opens a few neutral example windows + Waybar,
# is captured, then torn down.
#
# Usage:
#   bin/hypr-screenshot.sh [output.png]
#
# Env overrides:
#   OUT     output PNG path (default: ./hyprland-showcase.png)
#   EDITOR_FILE  file shown in the editor pane (default: hypr config.lua)

# Safety flags
set -uo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-${OUT:-$REPO/hyprland-showcase.png}}"
EDITOR_FILE="${EDITOR_FILE:-$REPO/.config/hypr/config.lua}"
TERM_EMU="${TERMINAL:-alacritty}"

# Children we spawn against the nested instance, killed on exit
PIDS=()
HYPR_PID=""
TMPDIR="$(mktemp -d)"

cleanup() {
    local pid
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null
    done
    [ -n "$HYPR_PID" ] && kill "$HYPR_PID" 2>/dev/null
    rm -rf "$TMPDIR"
}
trap cleanup EXIT INT TERM

# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------
for bin in Hyprland hyprctl grim "$TERM_EMU"; do
    if ! command -v "$bin" >/dev/null 2>&1; then
        echo "Error: required tool '$bin' not found in PATH." >&2
        exit 1
    fi
done

# ---------------------------------------------------------------------------
# Launch an isolated Hyprland (nested Wayland window, no real input devices)
# ---------------------------------------------------------------------------
before="$(hyprctl instances -j 2>/dev/null | grep -o '"instance": "[^"]*"' | sort)"

WLR_BACKEND=headless WLR_LIBINPUT_NO_DEVICES=1 HYPRLAND_NO_RT=1 \
    setsid Hyprland >"$TMPDIR/hypr.log" 2>&1 &
HYPR_PID=$!

# Wait for the new instance to register
SIG=""
for _ in $(seq 1 30); do
    sleep 0.5
    after="$(hyprctl instances -j 2>/dev/null | grep -o '"instance": "[^"]*"' | sort)"
    SIG="$(comm -13 <(echo "$before") <(echo "$after") | sed 's/.*"instance": "//;s/".*//' | head -1)"
    [ -n "$SIG" ] && break
done
if [ -z "$SIG" ]; then
    echo "Error: nested Hyprland instance did not start (see $TMPDIR/hypr.log)." >&2
    cat "$TMPDIR/hypr.log" >&2
    exit 1
fi
echo "Isolated Hyprland instance: $SIG"

# Resolve its Wayland socket
SOCK="$(hyprctl instances -j | python3 -c \
    "import sys,json;print([i['wl_socket'] for i in json.load(sys.stdin) if i['instance']=='$SIG'][0])")"
export WAYLAND_DISPLAY="$SOCK"
export HYPRLAND_INSTANCE_SIGNATURE="$SIG"
sleep 1

# Nested in a Wayland session, Hyprland opens a window-sized output whose
# resolution tracks the host. For a deterministic, full-HD capture we add a
# virtual headless output and drop the nested one so windows land on it.
mons_before="$(hyprctl -i "$SIG" monitors -j | grep -o '"name": "[^"]*"')"
hyprctl -i "$SIG" output create headless >/dev/null
sleep 1
OUTPUT="$(comm -13 <(echo "$mons_before" | sort) \
    <(hyprctl -i "$SIG" monitors -j | grep -o '"name": "[^"]*"' | sort) \
    | sed 's/.*"name": "//;s/".*//' | head -1)"
OUTPUT="${OUTPUT:-HEADLESS-2}"
# Remove every other (nested) output so the headless one is sole + focused
while read -r m; do
    [ "$m" = "$OUTPUT" ] && continue
    hyprctl -i "$SIG" output remove "$m" >/dev/null 2>&1
done < <(hyprctl -i "$SIG" monitors -j | grep -o '"name": "[^"]*"' | sed 's/.*"name": "//;s/".*//')
# Optional resolution override, e.g. RES=2560x1440
[ -n "${RES:-}" ] && hyprctl -i "$SIG" eval \
    "hl.monitor({ output = \"$OUTPUT\", mode = \"$RES@60\", position = \"0x0\", scale = 1 })" >/dev/null
sleep 1
echo "Capturing output $OUTPUT"

# ---------------------------------------------------------------------------
# Populate the workspace with neutral example windows + Waybar
# ---------------------------------------------------------------------------
spawn() { "$@" >/dev/null 2>&1 & PIDS+=("$!"); sleep 1.5; }

# Waybar reads ~/.config/waybar/config (per-host symlink), like the real session
command -v waybar >/dev/null 2>&1 && spawn waybar

# Pane script (kept open so the terminal doesn't exit before capture)
cat >"$TMPDIR/ff.sh" <<EOF
#!/usr/bin/env bash
exec "\${SHELL:-bash}"
EOF
chmod +x "$TMPDIR/ff.sh"

# Editor pane showing the Hyprland config (if nvim is available)...
command -v nvim >/dev/null 2>&1 && spawn "$TERM_EMU" -e nvim "$EDITOR_FILE"
# ...plus a plain terminal greeting with fastfetch.
spawn "$TERM_EMU" -e bash "$TMPDIR/ff.sh"

#sleep 2

# Clear Hyprland's startup notifications (version/qtutils/config warning
# banner that otherwise sits in the top-right of the capture).
hyprctl -i "$SIG" dismissnotify >/dev/null 2>&1
# Show a tidy example notification in its place.
hyprctl -i "$SIG" notify 1 8000 "rgb(89b4fa)" "Hello, world!                      " >/dev/null 2>&1

# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------
mkdir -p "$(dirname "$OUT")"
if grim -o "$OUTPUT" "$OUT"; then
    echo "Saved showcase screenshot -> $OUT"
else
    echo "Error: grim capture failed." >&2
    exit 1
fi
