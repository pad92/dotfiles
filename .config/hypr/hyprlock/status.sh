#!/bin/sh

mains=""
batteries=""

for ps in /sys/class/power_supply/*; do
    [ -d "$ps" ] && [ -r "$ps/type" ] || continue
    type=$(cat "$ps/type" 2>/dev/null) || continue

    case "$type" in
        Mains)
            if [ "$(cat "$ps/online" 2>/dev/null)" = "1" ]; then
                mains=""
            fi
            ;;
        Battery)
            # Exclude peripheral batteries (mouse, keyboard, etc.).
            [ "$(cat "$ps/scope" 2>/dev/null)" = "Device" ] && continue
            cap=$(cat "$ps/capacity" 2>/dev/null) || continue
            case "$cap" in
                ''|*[!0-9]*) continue ;;
            esac

            if [ "$cap" -gt 90 ]; then icon=""
            elif [ "$cap" -gt 60 ]; then icon=""
            elif [ "$cap" -gt 40 ]; then icon=""
            elif [ "$cap" -gt 10 ]; then icon=""
            else icon=""; fi

            batteries="${batteries}${batteries:+  }${icon} ${cap}%"
            ;;
    esac
done

[ -n "$mains$batteries" ] || exit 0
printf '%s\n' "${mains}${mains:+${batteries:+ }}${batteries}"
