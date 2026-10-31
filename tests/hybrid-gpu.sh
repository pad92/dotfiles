#!/bin/sh
set -eu
repo=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
. "$repo/ansible/roles/dotfiles/files/home/.config/uwsm/gpu-devices.sh"
detector="$repo/ansible/roles/system/files/detect-hybrid-laptop.sh"

card() {
    mkdir -p "$tmp/$1/class/drm/$2/device" "$tmp/$1/dev" "$tmp/drivers/$3" "$tmp/$1/class/power_supply"
    ln -s "$tmp/drivers/$3" "$tmp/$1/class/drm/$2/device/driver"
    printf '%s\n' "$4" > "$tmp/$1/class/drm/$2/device/boot_vga"
    touch "$tmp/$1/dev/$2"
}
battery() {
    mkdir -p "$tmp/$1/class/power_supply/internal"
    printf 'Battery\n' > "$tmp/$1/class/power_supply/internal/type"
}
expect() {
    [ "$1" = "$2" ] || { printf 'Expected %s, got %s\n' "$1" "$2" >&2; exit 1; }
}

# Reversed enumeration must preserve Intel preference and NVIDIA availability.
card first card0 nvidia 0
card first card7 i915 1
battery first
expect "$tmp/first/dev/card7:$tmp/first/dev/card0" "$(hypr_gpu_devices "$tmp/first/class/drm" "$tmp/first/dev")"
expect true "$(sh "$detector" "$tmp/first")"
card reversed card9 nvidia 0
card reversed card2 xe 1
battery reversed
expect "$tmp/reversed/dev/card2:$tmp/reversed/dev/card9" "$(hypr_gpu_devices "$tmp/reversed/class/drm" "$tmp/reversed/dev")"
expect true "$(sh "$detector" "$tmp/reversed")"

# Connectors and missing device nodes must not enter Aquamarine's list.
card reversed card2-DP-1 xe 1
mkdir -p "$tmp/reversed/class/drm/card8/device"
ln -s "$tmp/drivers/xe" "$tmp/reversed/class/drm/card8/device/driver"
expect "$tmp/reversed/dev/card2:$tmp/reversed/dev/card9" "$(hypr_gpu_devices "$tmp/reversed/class/drm" "$tmp/reversed/dev")"

# Desktops and single-GPU laptops must not receive the hybrid PM rule.
card desktop card4 amdgpu 1
card desktop card3 nvidia 0
expect "$tmp/desktop/dev/card4:$tmp/desktop/dev/card3" "$(hypr_gpu_devices "$tmp/desktop/class/drm" "$tmp/desktop/dev")"
expect false "$(sh "$detector" "$tmp/desktop")"
battery desktop
printf 'Device\n' > "$tmp/desktop/class/power_supply/internal/scope"
expect false "$(sh "$detector" "$tmp/desktop")"
printf 'System\n' > "$tmp/desktop/class/power_supply/internal/scope"
expect true "$(sh "$detector" "$tmp/desktop")"
card single card5 nvidia 1
battery single
expect unknown "$(sh "$detector" "$tmp/single")"
expect "$tmp/single/dev/card5" "$(hypr_gpu_devices "$tmp/single/class/drm" "$tmp/single/dev")"
if hypr_gpu_devices "$tmp/absent" "$tmp/absent"; then
    printf 'Empty discovery should retain automatic GPU selection\n' >&2
    exit 1
fi
expect unknown "$(sh "$detector" "$tmp/absent")"
# A driver not yet loaded must not cause deletion of an existing PM rule.
card pending card6 i915 1
battery pending
expect unknown "$(sh "$detector" "$tmp/pending")"
# The boot display takes precedence over a dedicated Intel GPU.
card intel_pair card2 xe 0
card intel_pair card7 i915 1
expect "$tmp/intel_pair/dev/card7:$tmp/intel_pair/dev/card2" "$(hypr_gpu_devices "$tmp/intel_pair/class/drm" "$tmp/intel_pair/dev")"
# Multiple GPUs without a unique boot display leave selection to Aquamarine.
card ambiguous card2 xe 0
card ambiguous card7 i915 0
if hypr_gpu_devices "$tmp/ambiguous/class/drm" "$tmp/ambiguous/dev"; then
    printf 'Ambiguous GPU selection should use automatic discovery\n' >&2
    exit 1
fi
printf '1\n' > "$tmp/ambiguous/class/drm/card2/device/boot_vga"
printf '1\n' > "$tmp/ambiguous/class/drm/card7/device/boot_vga"
if hypr_gpu_devices "$tmp/ambiguous/class/drm" "$tmp/ambiguous/dev"; then
    printf 'Multiple boot GPUs should use automatic discovery\n' >&2
    exit 1
fi
# Missing/invalid battery metadata must preserve an existing PM rule.
card incomplete card2 i915 1
card incomplete card7 nvidia 0
mkdir -p "$tmp/incomplete/class/power_supply/internal"
expect unknown "$(sh "$detector" "$tmp/incomplete")"
printf '\n' > "$tmp/incomplete/class/power_supply/internal/type"
expect unknown "$(sh "$detector" "$tmp/incomplete")"
printf 'Battery\n' > "$tmp/incomplete/class/power_supply/internal/type"
printf 'Unknown\n' > "$tmp/incomplete/class/power_supply/internal/scope"
expect unknown "$(sh "$detector" "$tmp/incomplete")"
# A non-boot Intel GPU alone is not evidence of integrated graphics.
card discrete card2 xe 0
card discrete card7 nvidia 1
battery discrete
expect unknown "$(sh "$detector" "$tmp/discrete")"
printf 'Hybrid GPU discovery tests passed\n'
