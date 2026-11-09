#!/usr/bin/env bash

# hypr-keybinds.sh - Show the keybindings Hyprland has loaded right now.
#
# The list comes from `hyprctl binds -j`, so it follows the live config:
# per-host binds and reloads show up without a second list to maintain.
# Binds without a `description` are still listed, under their dispatcher
# name, so a missing description is visible instead of hiding the bind.
#
# Usage: hypr-keybinds.sh [--print]
#   --print  write the list to stdout instead of opening Hyprlauncher

set -uo pipefail

# jq program: one line per bind, "MODS + KEY  —  description".
# jq has no bitwise operators, so modmask bits are tested by division.
# Modifier bits follow wlroots (SHIFT=1 CAPS=2 CTRL=4 ALT=8 MOD2=16 MOD3=32
# SUPER=64 MOD5=128); the order below is the order they are displayed in.
# Keycodes are XKB codes (evdev + 8) for the keys keybindings.lua binds by
# code; any other code is shown as `code:N`.
# shellcheck disable=SC2016 # $vars below belong to jq, not to the shell
FORMAT_BINDS='
def modifiers:
  . as $mask
  | [[64, "SUPER"], [4, "CTRL"], [8, "ALT"], [1, "SHIFT"],
     [2, "CAPS"], [16, "MOD2"], [32, "MOD3"], [128, "MOD5"]]
  | map(select((($mask / .[0]) | floor) % 2 == 1) | .[1]);

def keycodes:
  {"10": "1", "11": "2", "12": "3", "13": "4", "14": "5",
   "15": "6", "16": "7", "17": "8", "18": "9", "19": "0",
   "79": "KP_7", "80": "KP_8", "81": "KP_9", "83": "KP_4", "84": "KP_5",
   "85": "KP_6", "87": "KP_1", "88": "KP_2", "89": "KP_3", "90": "KP_0"};

def mouse_buttons:
  {"272": "Left click", "273": "Right click", "274": "Middle click",
   "up": "Wheel up", "down": "Wheel down"};

def key_name:
  if .catch_all then "Any key"
  elif (.key // "") | startswith("mouse:") then
    (.key | ltrimstr("mouse:")) as $button | mouse_buttons[$button] // .key
  elif (.key // "") != "" then .key
  else ((.keycode // 0) | tostring) as $code | keycodes[$code] // "code:\($code)"
  end;

def action:
  if .has_description and (.description // "") != "" then .description
  else
    (.dispatcher // "?") as $dispatcher
    # capture() yields nothing on a mismatch, which would drop the bind.
    | ($dispatcher | capture("^HL\\.Dispatcher\\((?<name>.*)\\)$").name // null) as $lua_name
    # Lua dispatchers carry an internal handle as arg, which means nothing
    # to a reader; legacy dispatchers carry the real argument.
    | if $lua_name then $lua_name
      else ([$dispatcher, (.arg // "" | tostring)] | map(select(. != "")) | join(" "))
      end
  end;

.[]
| ((.submap // "") | if . == "" then "" else "[\(.)] " end) as $submap
| ((((.modmask // 0) | modifiers) + [key_name]) | join(" + ")) as $keys
| "\($submap)\($keys)  —  \(action)"
'

# Read `hyprctl binds -j` output on stdin and print one line per bind.
format_binds()
{
    jq -r "$FORMAT_BINDS"
}

# A keybind has no terminal, so errors also go to a notification.
die()
{
    printf 'hypr-keybinds: %s\n' "$1" >&2
    if command -v notify-send >/dev/null 2>&1; then
        notify-send -a hypr-keybinds "Keybindings" "$1" >/dev/null 2>&1 || :
    fi
    exit 1
}

main()
{
    local print_only=false binds lines

    case "${1:-}" in
        "") ;;
        --print) print_only=true ;;
        *)
            printf 'Usage: %s [--print]\n' "$0" >&2
            exit 2
            ;;
    esac

    for bin in hyprctl jq; do
        command -v "$bin" >/dev/null 2>&1 || die "'$bin' is not installed or not in PATH."
    done
    if ! "$print_only" && ! command -v hyprlauncher >/dev/null 2>&1; then
        die "'hyprlauncher' is not installed or not in PATH."
    fi

    binds=$(hyprctl binds -j) || die "hyprctl binds failed; is Hyprland running?"
    lines=$(printf '%s' "$binds" | format_binds) || die "hyprctl returned binds that could not be read."
    [ -n "$lines" ] || die "Hyprland reported no keybindings."

    if "$print_only"; then
        printf '%s\n' "$lines"
        return 0
    fi

    # The selection is ignored: the list is for reading, not for running binds.
    printf '%s\n' "$lines" | hyprlauncher -m >/dev/null
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
