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

    # Keep configurations created before this option was introduced compatible.
    REMOTE_APPLY_TIMEOUT="${REMOTE_APPLY_TIMEOUT:-10}"
}

timeout_is_valid() {
    local value="$1"

    [[ "${value}" =~ ^[0-9]+([.][0-9]+)?$ ]] && [ -n "${value//[0.]/}" ]
}

validate_local_config() {
    if [ -z "${LOCAL_WALLPAPER_DIR-}" ]; then
        log "Error: LOCAL_WALLPAPER_DIR must not be empty."
        return 1
    fi
}

validate_remote_config() {
    if [ -z "${REMOTE_WALLPAPER_DIR-}" ]; then
        log "Error: REMOTE_WALLPAPER_DIR must not be empty."
        return 1
    fi

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
            if [ -n "${REMOTE_WALLPAPER_DIR-}" ]; then
                validate_remote_config
            fi
            ;;
        *)
            log "Error: WALLPAPER_SOURCE must be 'auto', 'local', or 'remote'."
            return 1
            ;;
    esac
}

require_commands() {
    local command_name

    for command_name in awww find mktemp sed shuf; do
        if ! command -v "${command_name}" >/dev/null 2>&1; then
            log "Error: '${command_name}' is not installed or not found in PATH."
            return 1
        fi
    done
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
    local filesystem_type
    local filesystem_types

    if ! command -v findmnt >/dev/null 2>&1 || ! command -v timeout >/dev/null 2>&1; then
        log "Warning: 'findmnt' and 'timeout' are required for remote wallpapers."
        return 1
    fi

    # Touch the path first so a dormant systemd automount exposes its real filesystem.
    if ! run_with_timeout "${REMOTE_PROBE_TIMEOUT}" \
        test -d "${REMOTE_WALLPAPER_DIR}"; then
        return 1
    fi

    if ! filesystem_types=$(run_with_timeout "${REMOTE_PROBE_TIMEOUT}" \
        findmnt --target "${REMOTE_WALLPAPER_DIR}" --noheadings --raw \
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
    local wallpaper_dir="$2"
    local image_list
    local -a find_command

    image_list=$(mktemp) || return 1
    find_command=(find -H "${wallpaper_dir}")

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
            "${find_command[@]}" > "${image_list}" 2>/dev/null; then
            rm -f "${image_list}"
            return 1
        fi
    elif ! "${find_command[@]}" > "${image_list}" 2>/dev/null; then
        rm -f "${image_list}"
        return 1
    fi

    IMAGES=()
    mapfile -d '' IMAGES < <(shuf -z "${image_list}")
    rm -f "${image_list}"

    [ "${#IMAGES[@]}" -gt 0 ]
}

load_wallpaper_source() {
    local wallpaper_source="$1"
    local wallpaper_dir="$2"

    if ! collect_images "${wallpaper_source}" "${wallpaper_dir}"; then
        return 1
    fi

    ACTIVE_WALLPAPER_SOURCE="${wallpaper_source}"
    ACTIVE_WALLPAPER_DIR="${wallpaper_dir}"
    log "Info: Using ${wallpaper_source} wallpapers from '${wallpaper_dir}'."
}

prepare_images() {
    case "${WALLPAPER_SOURCE}" in
        local)
            if ! load_wallpaper_source local "${LOCAL_WALLPAPER_DIR}"; then
                log "Error: No readable images found in '${LOCAL_WALLPAPER_DIR}'."
                return 1
            fi
            ;;
        remote)
            if ! remote_mount_is_supported; then
                log "Error: Remote wallpaper directory '${REMOTE_WALLPAPER_DIR}' is unavailable or uses an unsupported filesystem."
                return 1
            fi
            if ! load_wallpaper_source remote "${REMOTE_WALLPAPER_DIR}"; then
                log "Error: No readable images found in '${REMOTE_WALLPAPER_DIR}'."
                return 1
            fi
            ;;
        auto)
            if [ -n "${REMOTE_WALLPAPER_DIR-}" ] && remote_mount_is_supported; then
                if load_wallpaper_source remote "${REMOTE_WALLPAPER_DIR}"; then
                    return 0
                fi
                log "Warning: Remote wallpaper scan failed or returned no images."
            fi

            if ! load_wallpaper_source local "${LOCAL_WALLPAPER_DIR}"; then
                log "Error: No readable images found in '${LOCAL_WALLPAPER_DIR}'."
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
    local query

    query=$(awww query 2>/dev/null) || return 1
    [ -n "${query}" ] || return 1

    mapfile -t MONITORS < <(printf '%s\n' "${query}" | sed -E 's/^: ([^:]+):.*/\1/')
}

apply_image() {
    local monitor="$1"
    local image="$2"
    local -a command

    command=(awww img --outputs "${monitor}" "${image}" --resize=crop --transition-type fade)

    if [ "${ACTIVE_WALLPAPER_SOURCE}" = "remote" ]; then
        run_with_timeout "${REMOTE_APPLY_TIMEOUT}" "${command[@]}"
    else
        "${command[@]}"
    fi
}

apply_wallpapers() {
    local image
    local image_index=0
    local monitor
    local status=0

    for monitor in "${MONITORS[@]}"; do
        image="${IMAGES[image_index % ${#IMAGES[@]}]}"

        if ! apply_image "${monitor}" "${image}"; then
            if [ "${WALLPAPER_SOURCE}" = "auto" ] \
                && [ "${ACTIVE_WALLPAPER_SOURCE}" = "remote" ]; then
                log "Warning: Applying a remote wallpaper failed; switching to local images."
                if ! load_wallpaper_source local "${LOCAL_WALLPAPER_DIR}"; then
                    log "Error: Local wallpaper fallback is unavailable."
                    return 1
                fi
                image_index=0
                image="${IMAGES[image_index]}"
                apply_image "${monitor}" "${image}" || status=1
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
    ACTIVE_WALLPAPER_DIR=""
    ACTIVE_WALLPAPER_SOURCE=""

    prepare_images || return 1
    ensure_awww_daemon || return 1
    get_monitors || return 1

    [ "${#MONITORS[@]}" -gt 0 ] || return 0
    apply_wallpapers
}

main "$@"
