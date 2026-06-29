#!/usr/bin/env bash
#
# hypr-screenshot.sh — Render a clean showcase of this dotfiles' Hyprland
# configuration in an isolated, nested Hyprland instance and capture it with
# grim. Nothing from the live session leaks in: a fresh compositor is spawned,
# loads ~/.config/hypr (this repo), opens a few neutral example windows + Waybar,
# is captured, then torn down.
#
# The capture is encoded as a web-optimised WebP (lossy, q80, max effort) so it
# drops straight into docs/README without a heavy PNG.
#
# Usage:
#   bin/hypr-screenshot.sh [output.webp]
#
# Env overrides:
#   OUT      output WebP path (default: ./hyprland-showcase.webp)
#   WEBP_QUALITY  WebP quality 0-100 (default: 80)
#   EDITOR_FILE   file shown in the editor pane (default: hypr config.lua)

# Safety flags
set -uo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-${OUT:-$REPO/dist/hyprland.webp}}"
WEBP_QUALITY="${WEBP_QUALITY:-80}"
EDITOR_FILE="${EDITOR_FILE:-$REPO/README.md}"
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

# Pick a WebP encoder (cwebp gives the best size/quality, magick & ffmpeg fall back).
WEBP_ENCODER=""
for bin in cwebp magick convert ffmpeg; do
    command -v "$bin" >/dev/null 2>&1 && { WEBP_ENCODER="$bin"; break; }
done
if [ -z "$WEBP_ENCODER" ]; then
    echo "Error: no WebP encoder found (need one of: cwebp, magick, convert, ffmpeg)." >&2
    exit 1
fi

# Encode a PNG to a web-optimised WebP. $1=src png, $2=dst webp
encode_webp() {
    local src="$1" dst="$2"
    case "$WEBP_ENCODER" in
        cwebp)   cwebp -quiet -q "$WEBP_QUALITY" -m 6 "$src" -o "$dst" ;;
        magick)  magick "$src" -strip -quality "$WEBP_QUALITY" -define webp:method=6 "$dst" ;;
        convert) convert "$src" -strip -quality "$WEBP_QUALITY" -define webp:method=6 "$dst" ;;
        ffmpeg)  ffmpeg -loglevel error -y -i "$src" -c:v libwebp \
                     -compression_level 6 -quality "$WEBP_QUALITY" "$dst" ;;
    esac
}

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
# Capture (grim → PNG) then encode to a web-optimised WebP
# ---------------------------------------------------------------------------
mkdir -p "$(dirname "$OUT")"
RAW_PNG="$TMPDIR/capture.png"
if ! grim -o "$OUTPUT" "$RAW_PNG"; then
    echo "Error: grim capture failed." >&2
    exit 1
fi
if encode_webp "$RAW_PNG" "$OUT"; then
    echo "Saved showcase screenshot ($WEBP_ENCODER, WebP q$WEBP_QUALITY) -> $OUT"
else
    echo "Error: WebP encoding with '$WEBP_ENCODER' failed." >&2
    exit 1
fi
