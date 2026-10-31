#!/bin/sh
# Detect a host battery, a non-NVIDIA boot GPU and a separate NVIDIA GPU.
set -eu
sys_root=${1:-/sys}
if [ ! -d "$sys_root/class/power_supply" ] || [ ! -d "$sys_root/class/drm" ]; then
    printf 'unknown\n'
    exit 0
fi
battery=false
boot_gpu=false
nvidia=false
for supply in "$sys_root"/class/power_supply/*; do
    [ -e "$supply" ] || [ -L "$supply" ] || continue
    if ! supply_type=$(cat "$supply/type"); then
        printf 'unknown\n'
        exit 0
    fi
    if [ -z "$supply_type" ] || [ "$supply_type" = Unknown ]; then
        printf 'unknown\n'
        exit 0
    fi
    # Peripheral batteries (mouse, keyboard, headset) do not power the host.
    if [ -e "$supply/scope" ] || [ -L "$supply/scope" ]; then
        supply_scope=$(cat "$supply/scope") || supply_scope=Unknown
        case "$supply_scope" in
            Device) continue ;;
            System) ;;
            *) printf 'unknown\n'; exit 0 ;;
        esac
    fi
    if [ "$supply_type" = Battery ]; then
        battery=true
    fi
done
for card in "$sys_root"/class/drm/card[0-9]*; do
    name=${card##*/}
    case "${name#card}" in
        ''|*[!0-9]*) continue ;;
    esac
    driver=$(readlink "$card/device/driver") || continue
    case "${driver##*/}" in
        nvidia) nvidia=true ;;
        i915|xe|amdgpu)
            if [ -r "$card/device/boot_vga" ] &&
                [ "$(cat "$card/device/boot_vga")" = 1 ]; then
                boot_gpu=true
            fi
            ;;
    esac
done
if ! "$battery"; then
    printf 'false\n'
elif "$boot_gpu" && "$nvidia"; then
    printf 'true\n'
else
    # DRM exposes bound drivers only; absence does not prove missing hardware.
    printf 'unknown\n'
fi
