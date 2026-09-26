#!/usr/bin/env bash

set -uo pipefail

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/awww"
CONFIG_FILE="${AWWW_CONFIG_FILE:-${CONFIG_DIR}/awww.conf}"
CONFIG_SAMPLE_FILE="${CONFIG_FILE}-sample"

export AWWW_TRANSITION_FPS=30
export AWWW_TRANSITION_STEP=10

log() {
    printf '%s\n' "$*" >&2
}

normalize_directory_arrays() {
    if ! declare -p LOCAL_WALLPAPER_DIRS >/dev/null 2>&1; then
        LOCAL_WALLPAPER_DIRS=()
        if [ -n "${LOCAL_WALLPAPER_DIR-}" ]; then
            LOCAL_WALLPAPER_DIRS+=("${LOCAL_WALLPAPER_DIR}")
        fi
    fi

    if ! declare -p REMOTE_WALLPAPER_DIRS >/dev/null 2>&1; then
        REMOTE_WALLPAPER_DIRS=()
        if [ -n "${REMOTE_WALLPAPER_DIR-}" ]; then
            REMOTE_WALLPAPER_DIRS+=("${REMOTE_WALLPAPER_DIR}")
        fi
    fi
}

load_config() {
    local config_to_load

    if [ -r "${CONFIG_FILE}" ]; then
        config_to_load="${CONFIG_FILE}"
    elif [ -r "${CONFIG_SAMPLE_FILE}" ]; then
        config_to_load="${CONFIG_SAMPLE_FILE}"
        log "Info: '${CONFIG_FILE}' not found; using '${CONFIG_SAMPLE_FILE}'."
    else
        log "Error: Neither '${CONFIG_FILE}' nor '${CONFIG_SAMPLE_FILE}' is readable."
        return 1
    fi

    # shellcheck source=/dev/null
    source "${config_to_load}"

    normalize_directory_arrays

    # Keep configurations created before these options were introduced compatible.
    REMOTE_APPLY_TIMEOUT="${REMOTE_APPLY_TIMEOUT:-10}"
    AWWW_BLURRED_BACKGROUND="${AWWW_BLURRED_BACKGROUND:-true}"
    AWWW_BACKGROUND_BLUR="${AWWW_BACKGROUND_BLUR:-30}"
    AWWW_RENDER_CACHE_DIR="${AWWW_RENDER_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/awww/rendered}"
    AWWW_RENDER_THREADS="${AWWW_RENDER_THREADS:-2}"
    AWWW_RENDER_NICE="${AWWW_RENDER_NICE:-10}"
    AWWW_METADATA_OVERLAY="${AWWW_METADATA_OVERLAY:-true}"
    AWWW_METADATA_DATE_FORMAT="${AWWW_METADATA_DATE_FORMAT:-%d/%m/%Y}"
    AWWW_METADATA_FONT="${AWWW_METADATA_FONT:-DejaVu-Sans}"
    AWWW_METADATA_FONT_SIZE="${AWWW_METADATA_FONT_SIZE:-20}"
    AWWW_METADATA_MARGIN="${AWWW_METADATA_MARGIN:-36}"
}

timeout_is_valid() {
    local value="$1"

    [[ "${value}" =~ ^[0-9]+([.][0-9]+)?$ ]] && [ -n "${value//[0.]/}" ]
}

validate_directory_array() {
    local array_name="$1"
    local directory
    local declaration
    local -n directories="${array_name}"

    declaration=$(declare -p "${array_name}" 2>/dev/null) || return 1
    if [[ "${declaration}" != "declare -a "* ]]; then
        log "Error: ${array_name} must be a Bash array."
        return 1
    fi

    if [ "${#directories[@]}" -eq 0 ]; then
        log "Error: ${array_name} must contain at least one directory."
        return 1
    fi

    for directory in "${directories[@]}"; do
        if [ -z "${directory}" ]; then
            log "Error: ${array_name} must not contain empty paths."
            return 1
        fi
    done
}

validate_local_config() {
    validate_directory_array LOCAL_WALLPAPER_DIRS
}

validate_remote_config() {
    validate_directory_array REMOTE_WALLPAPER_DIRS || return 1

    if [ -z "${REMOTE_FS_TYPES-}" ]; then
        log "Error: REMOTE_FS_TYPES must not be empty."
        return 1
    fi

    if ! timeout_is_valid "${REMOTE_PROBE_TIMEOUT-}"; then
        log "Error: REMOTE_PROBE_TIMEOUT must be a positive number."
        return 1
    fi

    if ! timeout_is_valid "${REMOTE_SCAN_TIMEOUT-}"; then
        log "Error: REMOTE_SCAN_TIMEOUT must be a positive number."
        return 1
    fi

    if ! timeout_is_valid "${REMOTE_APPLY_TIMEOUT-}"; then
        log "Error: REMOTE_APPLY_TIMEOUT must be a positive number."
        return 1
    fi
}

validate_render_config() {
    case "${AWWW_BLURRED_BACKGROUND}" in
        true|false) ;;
        *)
            log "Error: AWWW_BLURRED_BACKGROUND must be 'true' or 'false'."
            return 1
            ;;
    esac

    case "${AWWW_METADATA_OVERLAY}" in
        true|false) ;;
        *)
            log "Error: AWWW_METADATA_OVERLAY must be 'true' or 'false'."
            return 1
            ;;
    esac

    if [ "${AWWW_BLURRED_BACKGROUND}" = "true" ] \
        && ! timeout_is_valid "${AWWW_BACKGROUND_BLUR}"; then
        log "Error: AWWW_BACKGROUND_BLUR must be a positive number."
        return 1
    fi

    if [ "${AWWW_METADATA_OVERLAY}" = "true" ]; then
        if [ -z "${AWWW_METADATA_DATE_FORMAT}" ] || [ -z "${AWWW_METADATA_FONT}" ]; then
            log "Error: Metadata date format and font must not be empty."
            return 1
        fi

        if ! timeout_is_valid "${AWWW_METADATA_FONT_SIZE}" \
            || ! timeout_is_valid "${AWWW_METADATA_MARGIN}"; then
            log "Error: Metadata font size and margin must be positive numbers."
            return 1
        fi
    fi

    if [ "${AWWW_BLURRED_BACKGROUND}" = "true" ] \
        || [ "${AWWW_METADATA_OVERLAY}" = "true" ]; then
        if [ -z "${AWWW_RENDER_CACHE_DIR}" ]; then
            log "Error: AWWW_RENDER_CACHE_DIR must not be empty."
            return 1
        fi

        if ! [[ "${AWWW_RENDER_THREADS}" =~ ^[1-9][0-9]*$ ]]; then
            log "Error: AWWW_RENDER_THREADS must be a positive integer."
            return 1
        fi

        if ! [[ "${AWWW_RENDER_NICE}" =~ ^[0-9]+$ ]] \
            || [ "${AWWW_RENDER_NICE}" -gt 19 ]; then
            log "Error: AWWW_RENDER_NICE must be an integer between 0 and 19."
            return 1
        fi
    fi
}

validate_config() {
    case "${WALLPAPER_SOURCE-}" in
        local)
            validate_local_config
            ;;
        remote)
            validate_remote_config
            ;;
        auto)
            validate_local_config || return 1
            if [ "${#REMOTE_WALLPAPER_DIRS[@]}" -gt 0 ]; then
                validate_remote_config
            fi
            ;;
        *)
            log "Error: WALLPAPER_SOURCE must be 'auto', 'local', or 'remote'."
            return 1
            ;;
    esac

    validate_render_config
}

require_commands() {
    local command_name

    for command_name in awww find mktemp shuf; do
        if ! command -v "${command_name}" >/dev/null 2>&1; then
            log "Error: '${command_name}' is not installed or not found in PATH."
            return 1
        fi
    done

    if [ "${AWWW_BLURRED_BACKGROUND}" = "true" ] \
        || [ "${AWWW_METADATA_OVERLAY}" = "true" ]; then
        for command_name in magick mkdir mv nice sha256sum stat; do
            if ! command -v "${command_name}" >/dev/null 2>&1; then
                log "Error: '${command_name}' is required to render wallpapers."
                return 1
            fi
        done
    fi

    if [ "${AWWW_METADATA_OVERLAY}" = "true" ] \
        && ! command -v exiftool >/dev/null 2>&1; then
        log "Error: 'exiftool' is required for the metadata overlay."
        return 1
    fi
}

run_with_timeout() {
    local duration="$1"
    shift

    timeout --kill-after=2s "${duration}" "$@"
}

filesystem_type_is_allowed() {
    local filesystem_type="$1"
    local allowed_type
    local -a allowed_types

    IFS=',' read -r -a allowed_types <<< "${REMOTE_FS_TYPES}"
    for allowed_type in "${allowed_types[@]}"; do
        if [ "${filesystem_type}" = "${allowed_type}" ]; then
            return 0
        fi
    done

    return 1
}

remote_mount_is_supported() {
    local remote_dir="$1"
    local filesystem_type
    local filesystem_types

    if ! command -v findmnt >/dev/null 2>&1 || ! command -v timeout >/dev/null 2>&1; then
        log "Warning: 'findmnt' and 'timeout' are required for remote wallpapers."
        return 1
    fi

    # Touch the path first so a dormant systemd automount exposes its real filesystem.
    if ! run_with_timeout "${REMOTE_PROBE_TIMEOUT}" \
        test -d "${remote_dir}"; then
        return 1
    fi

    if ! filesystem_types=$(run_with_timeout "${REMOTE_PROBE_TIMEOUT}" \
        findmnt --target "${remote_dir}" --noheadings --raw \
        --output FSTYPE 2>/dev/null); then
        return 1
    fi

    # An automount can report both autofs and its underlying NFS/CIFS filesystem.
    while IFS= read -r filesystem_type; do
        if filesystem_type_is_allowed "${filesystem_type}"; then
            return 0
        fi
    done <<< "${filesystem_types}"

    return 1
}

collect_images() {
    local wallpaper_source="$1"
    shift
    local directory
    local image_list
    local source_count=0
    local -a find_command

    image_list=$(mktemp) || return 1

    for directory in "$@"; do
        if [ "${wallpaper_source}" = "remote" ] \
            && ! remote_mount_is_supported "${directory}"; then
            log "Warning: Skipping unavailable remote directory '${directory}'."
            continue
        fi

        find_command=(find -H "${directory}")
        if [ "${wallpaper_source}" = "remote" ]; then
            find_command+=(-xdev)
        fi
        find_command+=(
            -type f
            \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \)
            -print0
        )

        if [ "${wallpaper_source}" = "remote" ]; then
            if ! run_with_timeout "${REMOTE_SCAN_TIMEOUT}" \
                "${find_command[@]}" >> "${image_list}" 2>/dev/null; then
                log "Warning: Failed to scan remote directory '${directory}'."
                continue
            fi
        elif ! "${find_command[@]}" >> "${image_list}" 2>/dev/null; then
            log "Warning: Failed to scan local directory '${directory}'."
            continue
        fi

        source_count=$((source_count + 1))
    done

    IMAGES=()
    mapfile -d '' IMAGES < <(shuf -z "${image_list}")
    rm -f "${image_list}"
    SOURCE_DIRECTORY_COUNT="${source_count}"

    [ "${#IMAGES[@]}" -gt 0 ]
}

load_wallpaper_sources() {
    local wallpaper_source="$1"
    local directory_label="directories"
    shift

    if ! collect_images "${wallpaper_source}" "$@"; then
        return 1
    fi

    if [ "${SOURCE_DIRECTORY_COUNT}" -eq 1 ]; then
        directory_label="directory"
    fi

    ACTIVE_WALLPAPER_SOURCE="${wallpaper_source}"
    log "Info: Using ${wallpaper_source} wallpapers from ${SOURCE_DIRECTORY_COUNT} ${directory_label}."
}

prepare_images() {
    case "${WALLPAPER_SOURCE}" in
        local)
            if ! load_wallpaper_sources local "${LOCAL_WALLPAPER_DIRS[@]}"; then
                log "Error: No readable images found in the local directories."
                return 1
            fi
            ;;
        remote)
            if ! load_wallpaper_sources remote "${REMOTE_WALLPAPER_DIRS[@]}"; then
                log "Error: No readable images found in the available remote directories."
                return 1
            fi
            ;;
        auto)
            if [ "${#REMOTE_WALLPAPER_DIRS[@]}" -gt 0 ]; then
                if load_wallpaper_sources remote "${REMOTE_WALLPAPER_DIRS[@]}"; then
                    return 0
                fi
                log "Warning: Remote wallpaper scans failed or returned no images."
            fi

            if ! load_wallpaper_sources local "${LOCAL_WALLPAPER_DIRS[@]}"; then
                log "Error: No readable images found in the local directories."
                return 1
            fi
            ;;
    esac
}

ensure_awww_daemon() {
    local attempts=50

    if ! awww query >/dev/null 2>&1; then
        if command -v systemctl >/dev/null 2>&1 \
            && systemctl --user list-unit-files awww.service >/dev/null 2>&1; then
            systemctl --user start awww.service >/dev/null 2>&1
        elif command -v awww-daemon >/dev/null 2>&1; then
            awww-daemon --no-cache >/dev/null 2>&1 &
        else
            log "Error: Unable to start awww-daemon."
            return 1
        fi
    fi

    while ! awww query >/dev/null 2>&1; do
        sleep 0.2
        attempts=$((attempts - 1))
        if [ "${attempts}" -le 0 ]; then
            log "Error: awww-daemon did not respond after 10 seconds."
            return 1
        fi
    done
}

get_monitors() {
    local line
    local query

    query=$(awww query 2>/dev/null) || return 1
    [ -n "${query}" ] || return 1

    while IFS= read -r line; do
        if [[ "${line}" =~ ^:[[:space:]]([^:]+):[[:space:]]([0-9]+x[0-9]+), ]]; then
            MONITORS+=("${BASH_REMATCH[1]}")
            MONITOR_SIZES+=("${BASH_REMATCH[2]}")
        fi
    done <<< "${query}"
}

run_for_active_source() {
    if [ "${ACTIVE_WALLPAPER_SOURCE}" = "remote" ]; then
        run_with_timeout "${REMOTE_APPLY_TIMEOUT}" "$@"
    else
        "$@"
    fi
}

read_photo_metadata() {
    local image="$1"
    local city_tag
    local photo_city=""
    local photo_date=""

    photo_date=$(run_for_active_source exiftool -s3 \
        -d "${AWWW_METADATA_DATE_FORMAT}" -DateTimeOriginal "${image}" \
        2>/dev/null) || photo_date=""
    if [ -z "${photo_date}" ]; then
        photo_date=$(run_for_active_source exiftool -s3 \
            -d "${AWWW_METADATA_DATE_FORMAT}" -CreateDate "${image}" \
            2>/dev/null) || photo_date=""
    fi
    photo_date="${photo_date%%$'\n'*}"

    for city_tag in City LocationShownCity LocationCreatedCity; do
        photo_city=$(run_for_active_source exiftool -s3 \
            "-${city_tag}" "${image}" 2>/dev/null) || photo_city=""
        photo_city="${photo_city%%$'\n'*}"
        [ -n "${photo_city}" ] && break
    done

    if [ -n "${photo_date}" ] && [ -n "${photo_city}" ]; then
        METADATA_LABEL="${photo_date} · ${photo_city}"
    elif [ -n "${photo_date}" ]; then
        METADATA_LABEL="${photo_date}"
    else
        METADATA_LABEL="${photo_city}"
    fi
}

prepare_display_image() {
    local dimensions="$1"
    local image="$2"
    local cache_key
    local cached_image
    local image_metadata
    local temporary_image
    local -a render_command

    if [ "${AWWW_BLURRED_BACKGROUND}" = "false" ] \
        && [ "${AWWW_METADATA_OVERLAY}" = "false" ]; then
        DISPLAY_IMAGE="${image}"
        DISPLAY_RESIZE_MODE="fit"
        return 0
    fi

    image_metadata=$(run_for_active_source stat --format='%Y:%s' "${image}") || return 1
    cache_key=$(printf '%s\n' \
        "v3|${image}|${image_metadata}|${dimensions}|${AWWW_BLURRED_BACKGROUND}|${AWWW_BACKGROUND_BLUR}|${AWWW_METADATA_OVERLAY}|${AWWW_METADATA_DATE_FORMAT}|${AWWW_METADATA_FONT}|${AWWW_METADATA_FONT_SIZE}|${AWWW_METADATA_MARGIN}" \
        | sha256sum) || return 1
    cache_key="${cache_key%% *}"

    mkdir -p "${AWWW_RENDER_CACHE_DIR}" || return 1
    cached_image="${AWWW_RENDER_CACHE_DIR}/${cache_key}.jpg"

    if [ ! -s "${cached_image}" ]; then
        METADATA_LABEL=""
        if [ "${AWWW_METADATA_OVERLAY}" = "true" ]; then
            read_photo_metadata "${image}"
        fi

        if [ "${AWWW_BLURRED_BACKGROUND}" = "false" ] \
            && [ -z "${METADATA_LABEL}" ]; then
            DISPLAY_IMAGE="${image}"
            DISPLAY_RESIZE_MODE="fit"
            return 0
        fi

        temporary_image=$(mktemp --tmpdir="${AWWW_RENDER_CACHE_DIR}" \
            '.awww-render.XXXXXX.jpg') || return 1

        if [ "${AWWW_BLURRED_BACKGROUND}" = "true" ]; then
            render_command=(
                magick -limit thread "${AWWW_RENDER_THREADS}"
                "${image}" -auto-orient -write mpr:source +delete
                mpr:source -resize "${dimensions}^" -gravity center
                -extent "${dimensions}" -blur "0x${AWWW_BACKGROUND_BLUR}"
                \( mpr:source -resize "${dimensions}" \)
                -gravity center -composite
            )
        else
            render_command=(
                magick -limit thread "${AWWW_RENDER_THREADS}"
                -size "${dimensions}" xc:black
                \( "${image}" -auto-orient -resize "${dimensions}" \)
                -gravity center -composite
            )
        fi

        if [ -n "${METADATA_LABEL}" ]; then
            render_command+=(
                \( -background none -font "${AWWW_METADATA_FONT}"
                -pointsize "${AWWW_METADATA_FONT_SIZE}" -fill '#fffffff0'
                "label:${METADATA_LABEL}"
                \( +clone -background black -shadow '65x2+2+2' \)
                +swap -background none -layers merge \)
                -gravity southeast
                -geometry "+${AWWW_METADATA_MARGIN}+${AWWW_METADATA_MARGIN}"
                -composite
            )
        fi
        render_command+=(-strip -quality 92 "${temporary_image}")
        render_command=(nice -n "${AWWW_RENDER_NICE}" "${render_command[@]}")
        if command -v ionice >/dev/null 2>&1; then
            render_command=(ionice -c 3 "${render_command[@]}")
        fi

        if ! run_for_active_source "${render_command[@]}"; then
            rm -f "${temporary_image}"
            return 1
        fi

        mv "${temporary_image}" "${cached_image}" || return 1
    fi

    DISPLAY_IMAGE="${cached_image}"
    DISPLAY_RESIZE_MODE="no"
}

apply_image() {
    local dimensions="$1"
    local monitor="$2"
    local image="$3"
    local -a command

    prepare_display_image "${dimensions}" "${image}" || return 1
    command=(
        awww img --outputs "${monitor}" "${DISPLAY_IMAGE}"
        --resize="${DISPLAY_RESIZE_MODE}" --transition-type fade
    )

    run_for_active_source "${command[@]}"
}

apply_wallpapers() {
    local dimensions
    local image
    local image_index=0
    local monitor
    local monitor_index
    local status=0

    for monitor_index in "${!MONITORS[@]}"; do
        monitor="${MONITORS[monitor_index]}"
        dimensions="${MONITOR_SIZES[monitor_index]}"
        image="${IMAGES[image_index % ${#IMAGES[@]}]}"

        if ! apply_image "${dimensions}" "${monitor}" "${image}"; then
            if [ "${WALLPAPER_SOURCE}" = "auto" ] \
                && [ "${ACTIVE_WALLPAPER_SOURCE}" = "remote" ]; then
                log "Warning: Applying a remote wallpaper failed; switching to local images."
                if ! load_wallpaper_sources local "${LOCAL_WALLPAPER_DIRS[@]}"; then
                    log "Error: Local wallpaper fallback is unavailable."
                    return 1
                fi
                image_index=0
                image="${IMAGES[image_index]}"
                apply_image "${dimensions}" "${monitor}" "${image}" || status=1
            else
                status=1
            fi
        fi

        image_index=$((image_index + 1))
    done

    return "${status}"
}

main() {
    load_config || return 1
    validate_config || return 1
    require_commands || return 1

    IMAGES=()
    MONITORS=()
    MONITOR_SIZES=()
    ACTIVE_WALLPAPER_SOURCE=""
    SOURCE_DIRECTORY_COUNT=0
    DISPLAY_IMAGE=""
    DISPLAY_RESIZE_MODE=""

    prepare_images || return 1
    ensure_awww_daemon || return 1
    get_monitors || return 1

    [ "${#MONITORS[@]}" -gt 0 ] || return 0
    apply_wallpapers
}

main "$@"
