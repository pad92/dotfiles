#!/bin/sh

mains=""
batteries=""

# Reads the first line of a sysfs attribute without starting a process.
attr()
{
    IFS= read -r value 2>/dev/null < "$1"
}

for ps in /sys/class/power_supply/*; do
    [ -d "$ps" ] && [ -r "$ps/type" ] || continue
    attr "$ps/type" || continue
    type=$value

    case "$type" in
        Mains|USB|USB_C|USB_PD|USB_PD_DRP|USB_DCP|USB_CDP|USB_ACA|Wireless)
            if attr "$ps/online" && [ "$value" = "1" ]; then
                mains=""
            fi
            ;;
        Battery)
            # Exclude peripheral batteries (mouse, keyboard, etc.).
            attr "$ps/scope" && [ "$value" = "Device" ] && continue
            attr "$ps/capacity" || continue
            cap=$value
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
