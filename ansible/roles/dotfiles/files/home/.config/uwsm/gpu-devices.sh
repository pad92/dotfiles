# shellcheck shell=sh
# POSIX shell, sourced by UWSM. Optional roots allow isolated fixture tests.
hypr_gpu_devices() (
    gpu_sysfs=${1:-/sys/class/drm}
    gpu_devfs=${2:-/dev/dri}
    gpu_count=0
    gpu_boot_count=0
    gpu_boot=
    gpu_other=
    for gpu_card in "$gpu_sysfs"/card[0-9]*; do
        gpu_name=${gpu_card##*/}
        case "${gpu_name#card}" in
            ''|*[!0-9]*) continue ;;
        esac
        [ -e "$gpu_devfs/$gpu_name" ] || continue
        [ -L "$gpu_card/device/driver" ] || continue
        gpu_node="$gpu_devfs/$gpu_name"
        gpu_count=$((gpu_count + 1))
        if [ -r "$gpu_card/device/boot_vga" ] &&
            [ "$(cat "$gpu_card/device/boot_vga")" = 1 ]; then
            gpu_boot="${gpu_boot:+$gpu_boot:}$gpu_node"
            gpu_boot_count=$((gpu_boot_count + 1))
        else
            gpu_other="${gpu_other:+$gpu_other:}$gpu_node"
        fi
    done
    # Driver names do not distinguish integrated GPUs from dedicated cards.
    # Keep Aquamarine's automatic selection when firmware gives no unique hint.
    if [ "$gpu_count" -gt 1 ] && [ "$gpu_boot_count" -ne 1 ]; then
        printf 'UWSM: no unique boot GPU; leaving GPU selection unchanged\n' >&2
        return 1
    fi
    gpu_result=
    for gpu_group in "$gpu_boot" "$gpu_other"; do
        [ -n "$gpu_group" ] || continue
        gpu_result="${gpu_result:+$gpu_result:}$gpu_group"
    done
    [ -n "$gpu_result" ] || return 1
    printf '%s\n' "$gpu_result"
)
