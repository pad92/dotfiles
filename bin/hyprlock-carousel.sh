#!/usr/bin/env bash

set -uo pipefail

CAROUSEL_IMAGE="${HOME}/.config/hypr/hyprlock/carousel-image.sh"
CAROUSEL_TEMPLATE="${HOME}/.config/hypr/hyprlock-carousel.conf"
CACHE_DIR="${XDG_CACHE_HOME:-${HOME}/.cache}/hyprlock-carousel"
BACKGROUND_FILE="${CACHE_DIR}/backgrounds.conf"
GENERATED_CONFIG="${CACHE_DIR}/hyprlock.conf"
MONITOR_FILE="${CACHE_DIR}/monitors"

lock_with_default_config() {
    exec hyprlock -c "${HOME}/.config/hypr/hyprlock.conf" "$@"
}

if [ ! -x "${CAROUSEL_IMAGE}" ] || [ ! -r "${CAROUSEL_TEMPLATE}" ]; then
    printf 'Warning: Carousel files are unavailable; starting the regular lock screen.\n' >&2
    lock_with_default_config "$@"
fi

if ! clock_font=$("${CAROUSEL_IMAGE}" --font); then
    printf 'Warning: Unable to resolve the carousel clock font; starting the regular lock screen.\n' >&2
    lock_with_default_config "$@"
fi

if ! command -v jq >/dev/null 2>&1; then
    printf "Warning: 'jq' is unavailable; starting the regular lock screen.\n" >&2
    lock_with_default_config "$@"
fi

: > "${BACKGROUND_FILE}"
if ! hyprctl monitors -j | jq -r '.[] | select(.disabled | not) | [.name, ((.width | tostring) + "x" + (.height | tostring))] | @tsv' > "${MONITOR_FILE}"; then
    printf 'Warning: Unable to detect monitors; starting the regular lock screen.\n' >&2
    lock_with_default_config "$@"
fi

monitor_count=0
while IFS=$'\t' read -r monitor dimensions; do
    [ -n "${monitor}" ] || continue
    if ! [[ "${monitor}" =~ ^[A-Za-z0-9_.-]+$ ]] \
        || ! [[ "${dimensions}" =~ ^[1-9][0-9]*x[1-9][0-9]*$ ]]; then
        printf 'Warning: Invalid monitor data; starting the regular lock screen.\n' >&2
        lock_with_default_config "$@"
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
    printf 'Warning: No active Hyprland monitor found; starting the regular lock screen.\n' >&2
    lock_with_default_config "$@"
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
' "${CAROUSEL_TEMPLATE}" > "${GENERATED_CONFIG}" || lock_with_default_config "$@"

hyprlock -c "${GENERATED_CONFIG}" "$@" &
hyprlock_pid=$!

# Let Hyprlock install its SIGUSR2 handler before the first image is ready.
sleep 1

prepare_carousel_images() {
    local monitor
    local dimensions

    "${CAROUSEL_IMAGE}" --refresh >/dev/null || return 1
    while IFS=$'\t' read -r monitor dimensions; do
        [ -n "${monitor}" ] || continue
        if ! "${CAROUSEL_IMAGE}" "${monitor}" "${dimensions}" >/dev/null; then
            printf "Warning: Unable to prepare the carousel for monitor '%s'.\n" "${monitor}" >&2
            return 1
        fi
    done < "${MONITOR_FILE}"
}

if prepare_carousel_images; then
    kill -USR2 "${hyprlock_pid}" 2>/dev/null || true
else
    printf 'Warning: Carousel preparation failed; the lock screen remains active with a plain background.\n' >&2
fi

wait "${hyprlock_pid}"
