#!/bin/sh
# Print "<render node> <kernel driver> <boot_vga>" for each DRM render node.
set -eu
sys_root=${1:-/sys}
for node in "$sys_root"/class/drm/renderD*; do
    [ -e "$node" ] || continue
    driver=$(readlink "$node/device/driver") || continue
    boot_vga=0
    if [ -r "$node/device/boot_vga" ]; then
        boot_vga=$(cat "$node/device/boot_vga")
    fi
    printf '%s %s %s\n' "${node##*/}" "${driver##*/}" "$boot_vga"
done
