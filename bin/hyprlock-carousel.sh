#!/usr/bin/env bash

set -uo pipefail

CAROUSEL_IMAGE="${HOME}/.config/hypr/hyprlock/carousel-image.sh"
CAROUSEL_TEMPLATE="${HOME}/.config/hypr/hyprlock-carousel.conf"
CACHE_DIR="${XDG_CACHE_HOME:-${HOME}/.cache}/hyprlock-carousel"
BACKGROUND_FILE="${CACHE_DIR}/backgrounds.conf"
GENERATED_CONFIG="${CACHE_DIR}/hyprlock.conf"
MONITOR_FILE="${CACHE_DIR}/monitors"
DPMS_INHIBIT_FILE="${XDG_RUNTIME_DIR:-${HOME}/.cache}/hyprlock-carousel.dpms-inhibit"
CAROUSEL_INTERVAL=60

lock_with_default_config() {
    exec hyprlock -c "${HOME}/.config/hypr/hyprlock.conf" "$@"
}

start_regular_lock() {
    local reason="$1"
    shift

    printf 'Warning: %s; starting the regular lock screen.\n' "${reason}" >&2
    lock_with_default_config "$@" || exit $?
}

if [ ! -x "${CAROUSEL_IMAGE}" ] || [ ! -r "${CAROUSEL_TEMPLATE}" ]; then
    start_regular_lock 'Carousel files are unavailable' "$@"
fi

if ! clock_font=$("${CAROUSEL_IMAGE}" --font); then
    start_regular_lock 'Unable to resolve the carousel clock font' "$@"
fi

if ! command -v jq >/dev/null 2>&1; then
    start_regular_lock "'jq' is unavailable" "$@"
fi

: > "${BACKGROUND_FILE}"
if ! hyprctl monitors -j | jq -r '.[] | select(.disabled | not) | [.name, ((.width | tostring) + "x" + (.height | tostring))] | @tsv' > "${MONITOR_FILE}"; then
    start_regular_lock 'Unable to detect monitors' "$@"
fi

monitor_count=0
while IFS=$'\t' read -r monitor dimensions; do
    [ -n "${monitor}" ] || continue
    if ! [[ "${monitor}" =~ ^[A-Za-z0-9_.-]+$ ]] \
        || ! [[ "${dimensions}" =~ ^[1-9][0-9]*x[1-9][0-9]*$ ]]; then
        start_regular_lock 'Invalid monitor data' "$@"
    fi

    cat >> "${BACKGROUND_FILE}" <<EOF
background {
    monitor = ${monitor}
    color = rgba(29, 32, 33, 1.0)
    reload_time = 0
    reload_cmd = ${CAROUSEL_IMAGE} --current ${monitor}
    blur_size = 8
    blur_passes = 0
    noise = 0.0117
    contrast = 1.3000
    brightness = 0.8000
    vibrancy = 0.2100
    vibrancy_darkness = 0.0
}

EOF
    monitor_count=$((monitor_count + 1))
done < "${MONITOR_FILE}"

if [ "${monitor_count}" -eq 0 ]; then
    start_regular_lock 'No active Hyprland monitor found' "$@"
fi

awk -v backgrounds="${BACKGROUND_FILE}" -v clock_font="${clock_font}" '
    /^\$clock_font_family[[:space:]]*=/ {
        print "$clock_font_family = " clock_font
        next
    }
    !replaced && /^background[[:space:]]*\{/ {
        while ((getline line < backgrounds) > 0) print line
        close(backgrounds)
        replaced = 1
        skipping = 1
        next
    }
    skipping {
        if (/^}/) skipping = 0
        next
    }
    { print }
' "${CAROUSEL_TEMPLATE}" > "${GENERATED_CONFIG}" \
    || start_regular_lock 'Unable to generate the carousel configuration' "$@"

mkdir -p "$(dirname -- "${DPMS_INHIBIT_FILE}")"
: > "${DPMS_INHIBIT_FILE}"
trap 'rm -f -- "${DPMS_INHIBIT_FILE}"' EXIT

hyprlock -c "${GENERATED_CONFIG}" "$@" &
hyprlock_pid=$!

# Let Hyprlock install its SIGUSR2 handler before the first image is ready.
sleep 1
if ! kill -0 "${hyprlock_pid}" 2>/dev/null; then
    printf 'Error: Hyprlock exited before the carousel was ready.\n' >&2
    wait "${hyprlock_pid}"
    exit $?
fi

prepare_carousel_images() {
    local refresh_image_list="${1:-false}"
    local monitor
    local dimensions

    if [ "${refresh_image_list}" = true ]; then
        "${CAROUSEL_IMAGE}" --refresh >/dev/null || return 1
    fi

    while IFS=$'\t' read -r monitor dimensions; do
        [ -n "${monitor}" ] || continue
        if ! "${CAROUSEL_IMAGE}" "${monitor}" "${dimensions}" >/dev/null; then
            printf "Warning: Unable to prepare the carousel for monitor '%s'.\n" "${monitor}" >&2
            return 1
        fi
    done < "${MONITOR_FILE}"
}

rotate_carousel() {
    local sleep_pid=""

    # Keep image rendering out of Hyprlock's reload command.
    trap 'if [ -n "${sleep_pid}" ]; then kill "${sleep_pid}" 2>/dev/null || true; fi' TERM
    while kill -0 "${hyprlock_pid}" 2>/dev/null; do
        sleep "${CAROUSEL_INTERVAL}" &
        sleep_pid=$!
        wait "${sleep_pid}" || break
        sleep_pid=""

        kill -0 "${hyprlock_pid}" 2>/dev/null || break
        if ! prepare_carousel_images; then
            printf 'Warning: Unable to prepare the next carousel images.\n' >&2
            continue
        fi

        if kill -0 "${hyprlock_pid}" 2>/dev/null; then
            kill -USR2 "${hyprlock_pid}" 2>/dev/null || break
        else
            break
        fi
    done
}

rotation_pid=""
if prepare_carousel_images true; then
    if kill -USR2 "${hyprlock_pid}" 2>/dev/null; then
        rotate_carousel &
        rotation_pid=$!
    else
        printf 'Warning: Unable to reload the first carousel images.\n' >&2
    fi
else
    printf 'Warning: Carousel preparation failed; the lock screen remains active with a plain background.\n' >&2
fi

if wait "${hyprlock_pid}"; then
    hyprlock_status=0
else
    hyprlock_status=$?
fi

if [ -n "${rotation_pid}" ]; then
    kill -TERM "${rotation_pid}" 2>/dev/null || true
    wait "${rotation_pid}" 2>/dev/null || true
fi

exit "${hyprlock_status}"
