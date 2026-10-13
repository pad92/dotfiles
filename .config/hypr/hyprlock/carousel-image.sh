#!/usr/bin/env bash

set -uo pipefail

AWWW_SCRIPT="${HOME}/.dotfiles/bin/awww.sh"
CACHE_DIR="${XDG_CACHE_HOME:-${HOME}/.cache}/hyprlock-carousel"
IMAGE_INDEX="${CACHE_DIR}/index"
IMAGE_LIST="${CACHE_DIR}/images"
IMAGE_SOURCE="${CACHE_DIR}/source"
LOCK_FILE="${CACHE_DIR}/lock"

log() {
    printf '%s\n' "$*" >&2
}

load_awww() {
    if [ ! -r "${AWWW_SCRIPT}" ]; then
        log "Error: '${AWWW_SCRIPT}' is not readable."
        return 1
    fi

    # shellcheck source=/dev/null
    source "${AWWW_SCRIPT}"
    load_config || return 1
    validate_config || return 1
}

refresh_image_list() {
    local temporary_list
    local temporary_source

    load_awww || return 1

    for command_name in find mktemp shuf; do
        if ! command -v "${command_name}" >/dev/null 2>&1; then
            log "Error: '${command_name}' is not installed or not found in PATH."
            return 1
        fi
    done

    IMAGES=()
    prepare_images || return 1

    temporary_list="${CACHE_DIR}/.images.$$"
    temporary_source="${CACHE_DIR}/.source.$$"
    printf '%s\0' "${IMAGES[@]}" > "${temporary_list}" || return 1
    printf '%s\n' "${ACTIVE_WALLPAPER_SOURCE}" > "${temporary_source}" || return 1
    mv -f -- "${temporary_list}" "${IMAGE_LIST}" || return 1
    mv -f -- "${temporary_source}" "${IMAGE_SOURCE}" || return 1
    printf '0\n' > "${IMAGE_INDEX}"
}

render_next_image() {
    local dimensions="$1"
    local monitor="$2"
    local current_image
    local image_index
    local next_index
    local selected_image
    local temporary_index
    local temporary_link

    load_awww || return 1
    require_commands || return 1
    resolve_metadata_font || return 1

    ACTIVE_WALLPAPER_SOURCE=$(cat "${IMAGE_SOURCE}") || return 1
    IMAGES=()
    mapfile -d '' IMAGES < "${IMAGE_LIST}"
    [ "${#IMAGES[@]}" -gt 0 ] || return 1

    image_index=$(cat "${IMAGE_INDEX}" 2>/dev/null || printf '0')
    if ! [[ "${image_index}" =~ ^[0-9]+$ ]]; then
        image_index=0
    fi

    selected_image="${IMAGES[image_index % ${#IMAGES[@]}]}"
    next_index=$(((image_index + 1) % ${#IMAGES[@]}))
    prepare_display_image "${dimensions}" "${selected_image}" || return 1

    current_image="${CACHE_DIR}/current-${monitor}"
    temporary_link="${CACHE_DIR}/.current-${monitor}.$$"
    temporary_index="${CACHE_DIR}/.index.$$"
    trap 'rm -f -- "${temporary_link}" "${temporary_index}"' RETURN
    ln -s -- "${DISPLAY_IMAGE}" "${temporary_link}" || return 1
    printf '%s\n' "${next_index}" > "${temporary_index}" || return 1
    mv -Tf -- "${temporary_link}" "${current_image}" || return 1
    mv -f -- "${temporary_index}" "${IMAGE_INDEX}" || return 1
    trap - RETURN

    printf '%s\n' "${DISPLAY_IMAGE}"
}

mkdir -p "${CACHE_DIR}" || exit 1
if ! command -v flock >/dev/null 2>&1; then
    log "Error: 'flock' is not installed or not found in PATH."
    exit 1
fi
exec 9> "${LOCK_FILE}"
flock 9

if [ "${1-}" = "--refresh" ]; then
    refresh_image_list
    exit $?
fi

if [ "${1-}" = "--current" ]; then
    if [ "$#" -ne 2 ] || ! [[ "$2" =~ ^[A-Za-z0-9_.-]+$ ]]; then
        log "Usage: $0 --current MONITOR"
        exit 1
    fi
    printf '%s/current-%s\n' "${CACHE_DIR}" "$2"
    exit 0
fi

if [ "${1-}" = "--font" ]; then
    load_awww || exit 1
    if ! command -v magick >/dev/null 2>&1; then
        log "Error: 'magick' is required to resolve the clock font."
        exit 1
    fi
    resolve_metadata_font || exit 1
    printf '%s\n' "${AWWW_METADATA_FONT}"
    exit 0
fi

if [ "$#" -ne 2 ] || ! [[ "$1" =~ ^[A-Za-z0-9_.-]+$ ]] \
    || ! [[ "$2" =~ ^[1-9][0-9]*x[1-9][0-9]*$ ]]; then
    log "Usage: $0 --refresh | --current MONITOR | --font | MONITOR WIDTHxHEIGHT"
    exit 1
fi

if [ ! -s "${IMAGE_LIST}" ] || [ ! -s "${IMAGE_SOURCE}" ]; then
    refresh_image_list || exit 1
fi

render_next_image "$2" "$1"
