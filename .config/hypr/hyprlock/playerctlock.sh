#!/usr/bin/env bash

set -u

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P) || exit 1
readonly SCRIPT_DIR
readonly EMPTY_FILE="$SCRIPT_DIR/empty.png"
readonly MAX_ART_BYTES=$((10 * 1024 * 1024))
readonly MAX_METADATA_CHARS=120
readonly CACHE_MAX_AGE_MINUTES=60
readonly CACHE_RETENTION_MINUTES=1440
readonly FAILURE_RETRY_MINUTES=5
readonly MAX_CACHE_FILES=100
readonly MAX_CACHE_ARTIFACTS=300

usage()
{
    echo "Usage: $0 --title | --arturl | --artist | --length | --status | --album | --source"
}

get_metadata()
{
    local key=$1
    timeout 2s playerctl metadata --format "{{ $key }}" 2>/dev/null || true
}

get_status()
{
    timeout 2s playerctl status 2>/dev/null || true
}

escape_metadata()
{
    local value=$1

    value=${value//$'\r'/ }
    value=${value//$'\n'/ }
    value=${value//$'\t'/ }
    if (( ${#value} > MAX_METADATA_CHARS )); then
        value="${value:0:MAX_METADATA_CHARS}…"
    fi
    value=${value//&/\&amp;}
    value=${value//</\&lt;}
    value=${value//>/\&gt;}
    printf '%s\n' "$value"
}

get_web_source_info()
{
    local media_url authority host port label
    local -a host_labels

    media_url=${1,,}
    case "$media_url" in
        http://*|https://*) ;;
        *) return 1 ;;
    esac

    authority=${media_url#*://}
    authority=${authority%%[/?#]*}
    authority=${authority##*@}
    case "$authority" in
        \[*\]*) return 1 ;;
        *:*)
            host=${authority%%:*}
            port=${authority#*:}
            [[ $port =~ ^[0-9]{1,5}$ ]] || return 1
            (( 10#$port >= 1 && 10#$port <= 65535 )) || return 1
            ;;
        *) host=$authority ;;
    esac
    host=${host%.}
    [[ $host != *. ]] || return 1
    host=${host#www.}

    (( ${#host} <= 253 )) || return 1
    IFS=. read -r -a host_labels <<< "$host"
    (( ${#host_labels[@]} > 0 )) || return 1
    for label in "${host_labels[@]}"; do
        (( ${#label} <= 63 )) || return 1
        [[ $label =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]] || return 1
    done

    case "$host" in
        deezer.com|*.deezer.com) printf 'Deezer \uE077 \n' ;;
        music.youtube.com) echo "YouTube Music  " ;;
        youtube.com|*.youtube.com|youtu.be) echo "YouTube  " ;;
        spotify.com|*.spotify.com) echo "Spotify  " ;;
        soundcloud.com|*.soundcloud.com) echo "SoundCloud  " ;;
        twitch.tv|*.twitch.tv) echo "Twitch  " ;;
        netflix.com|*.netflix.com) echo "Netflix 󰝆 " ;;
        primevideo.com|*.primevideo.com) echo "Prime Video  " ;;
        disneyplus.com|*.disneyplus.com) echo "Disney+ 󰿎 " ;;
        music.apple.com) echo "Apple Music  " ;;
        bandcamp.com|*.bandcamp.com) echo "Bandcamp  " ;;
        tidal.com|*.tidal.com) echo "Tidal  " ;;
        vimeo.com|*.vimeo.com) echo "Vimeo  " ;;
        *) printf '%s  \n' "$(escape_metadata "$host")" ;;
    esac
}

get_source_info()
{
    local player_name media_url

    player_name=$(get_metadata "playerName")
    case "${player_name,,}" in
        *firefox*)
            media_url=$(get_metadata "xesam:url")
            get_web_source_info "$media_url" || echo "Firefox  "
            ;;
        *chromium*|*chrome*)
            media_url=$(get_metadata "xesam:url")
            get_web_source_info "$media_url" || echo "Chrome  "
            ;;
        *spotify*) echo "Spotify  " ;;
        *) echo "" ;;
    esac
}

init_art_dir()
{
    local uid cache_file
    local -a excess_cache_files

    uid=$(id -u) || return 1
    if [[ -n ${XDG_RUNTIME_DIR:-} && -d $XDG_RUNTIME_DIR && ! -L $XDG_RUNTIME_DIR \
        && -w $XDG_RUNTIME_DIR && $(stat -c %u -- "$XDG_RUNTIME_DIR" 2>/dev/null) == "$uid" ]]; then
        ART_DIR="$XDG_RUNTIME_DIR/hyprlock-mpris"
    else
        ART_DIR="${TMPDIR:-/tmp}/hyprlock-mpris-$uid"
    fi

    [[ ! -L $ART_DIR ]] || return 1
    umask 077
    if [[ ! -e $ART_DIR ]]; then
        mkdir -m 700 -- "$ART_DIR" || return 1
    fi
    [[ -d $ART_DIR && ! -L $ART_DIR \
        && $(stat -c %u -- "$ART_DIR" 2>/dev/null) == "$uid" ]] || return 1
    chmod 700 -- "$ART_DIR" || return 1
    find "$ART_DIR" -maxdepth 1 -type f -name 'mpris_artUrl_*' \
        -mmin "+$CACHE_RETENTION_MINUTES" -delete 2>/dev/null || true

    mapfile -t excess_cache_files < <(
        find "$ART_DIR" -maxdepth 1 -type f -name 'mpris_artUrl_*.png' \
            -printf '%T@ %f\n' 2>/dev/null | sort -nr | awk -v keep="$MAX_CACHE_FILES" 'NR > keep { print $2 }'
    )
    for cache_file in "${excess_cache_files[@]}"; do
        rm -f -- "$ART_DIR/$cache_file" "$ART_DIR/$cache_file.lock" \
            "$ART_DIR/$cache_file.failed" "$ART_DIR/$cache_file.source"
    done

    mapfile -t excess_cache_files < <(
        find "$ART_DIR" -maxdepth 1 -type f -name 'mpris_artUrl_*' \
            -printf '%T@ %f\n' 2>/dev/null | sort -nr \
            | awk -v keep="$MAX_CACHE_ARTIFACTS" 'NR > keep { print $2 }'
    )
    for cache_file in "${excess_cache_files[@]}"; do
        rm -f -- "$ART_DIR/$cache_file"
    done
}

lock_cache_file()
{
    local lock_file=$1

    command -v flock >/dev/null 2>&1 || return 1
    exec {CACHE_LOCK_FD}>"$lock_file" || return 1
    flock -w 2 "$CACHE_LOCK_FD"
}

fallback_artwork()
{
    local stale_file=${1:-}
    local failure_file=${2:-}

    [[ -z $failure_file ]] || touch -- "$failure_file"
    if [[ -n $stale_file && -s $stale_file ]]; then
        echo "$stale_file"
    else
        echo "$EMPTY_FILE"
    fi
}

get_artwork()
{
    local url source_path cache_key art_file mime converter file_size
    local source_stamp stamp_file cached_stamp
    local stale_art_file="" failure_file=""

    init_art_dir || { echo "$EMPTY_FILE"; return; }
    url=$(get_metadata "mpris:artUrl")
    [[ -n $url ]] || { echo "$EMPTY_FILE"; return; }

    WORK_DIR=$(mktemp -d "$ART_DIR/mpris_artUrl.XXXXXXXXXX") || { echo "$EMPTY_FILE"; return; }
    trap 'rm -rf -- "$WORK_DIR"' EXIT
    trap 'exit 1' HUP INT TERM

    case "$url" in
        file://localhost/*)
            source_path=/${url#file://localhost/}
            ;;
        file:///*)
            source_path=${url#file://}
            ;;
        https://*)
            cache_key=$(printf '%s' "$url" | sha256sum) || { echo "$EMPTY_FILE"; return; }
            art_file="$ART_DIR/mpris_artUrl_${cache_key%% *}.png"
            failure_file="$art_file.failed"
            [[ ! -s $art_file ]] || stale_art_file=$art_file
            if [[ -n $stale_art_file ]] \
                && find "$art_file" -mmin "-$CACHE_MAX_AGE_MINUTES" -print -quit 2>/dev/null | grep -q .; then
                echo "$art_file"
                return
            fi
            if [[ -e $failure_file ]] \
                && find "$failure_file" -mmin "-$FAILURE_RETRY_MINUTES" -print -quit 2>/dev/null | grep -q .; then
                fallback_artwork "$stale_art_file"
                return
            fi

            if ! lock_cache_file "$art_file.lock"; then
                fallback_artwork "$stale_art_file"
                return
            fi
            if [[ -s $art_file ]] \
                && find "$art_file" -mmin "-$CACHE_MAX_AGE_MINUTES" -print -quit 2>/dev/null | grep -q .; then
                echo "$art_file"
                return
            fi
            if [[ -e $failure_file ]] \
                && find "$failure_file" -mmin "-$FAILURE_RETRY_MINUTES" -print -quit 2>/dev/null | grep -q .; then
                fallback_artwork "$stale_art_file"
                return
            fi

            source_path="$WORK_DIR/download"
            if ! curl -fsS --location \
                --proto '=https' --proto-redir '=https' \
                --connect-timeout 2 --max-time 5 --max-filesize "$MAX_ART_BYTES" \
                --output "$source_path" -- "$url"; then
                fallback_artwork "$stale_art_file" "$failure_file"
                return
            fi
            ;;
        *)
            echo "$EMPTY_FILE"
            return
            ;;
    esac

    if [[ $url == file://* ]]; then
        cache_key=$(printf '%s' "$url" | sha256sum) || { echo "$EMPTY_FILE"; return; }
        art_file="$ART_DIR/mpris_artUrl_${cache_key%% *}.png"
        stamp_file="$art_file.source"
        [[ ! -s $art_file ]] || stale_art_file=$art_file
        if [[ ! -f $source_path || ! -r $source_path ]]; then
            fallback_artwork "$stale_art_file"
            return
        fi

        source_stamp=$(stat -c '%y:%s' -- "$source_path" 2>/dev/null) \
            || { fallback_artwork "$stale_art_file"; return; }
        cached_stamp=$(cat -- "$stamp_file" 2>/dev/null || true)
        if [[ -n $stale_art_file && $cached_stamp == "$source_stamp" ]]; then
            echo "$art_file"
            return
        fi

        if ! lock_cache_file "$art_file.lock"; then
            fallback_artwork "$stale_art_file"
            return
        fi
        if [[ ! -f $source_path || ! -r $source_path ]]; then
            fallback_artwork "$stale_art_file"
            return
        fi
        source_stamp=$(stat -c '%y:%s' -- "$source_path" 2>/dev/null) \
            || { fallback_artwork "$stale_art_file"; return; }
        cached_stamp=$(cat -- "$stamp_file" 2>/dev/null || true)
        if [[ -s $art_file && $cached_stamp == "$source_stamp" ]]; then
            echo "$art_file"
            return
        fi
    fi

    [[ -f $source_path && -r $source_path ]] \
        || { fallback_artwork "$stale_art_file" "$failure_file"; return; }
    file_size=$(stat -c %s -- "$source_path" 2>/dev/null) \
        || { fallback_artwork "$stale_art_file" "$failure_file"; return; }
    (( file_size > 0 && file_size <= MAX_ART_BYTES )) \
        || { fallback_artwork "$stale_art_file" "$failure_file"; return; }

    mime=$(file --brief --mime-type -- "$source_path" 2>/dev/null) \
        || { fallback_artwork "$stale_art_file" "$failure_file"; return; }
    case "$mime" in
        image/gif|image/jpeg|image/png|image/webp) ;;
        *) fallback_artwork "$stale_art_file" "$failure_file"; return ;;
    esac

    if command -v magick >/dev/null 2>&1; then
        converter=magick
    elif command -v convert >/dev/null 2>&1; then
        converter=convert
    else
        fallback_artwork "$stale_art_file" "$failure_file"
        return
    fi

    if MAGICK_TMPDIR="$WORK_DIR" timeout --kill-after=1s 5s "$converter" \
        -limit memory 64MiB -limit map 128MiB -limit disk 128MiB \
        -limit time 4 -limit thread 2 -limit width 16384 \
        -limit height 16384 -limit list-length 2 \
        "${source_path}[0]" -resize '150x150^' -gravity center \
        -crop 150x150+0+0 +repage "PNG:$WORK_DIR/art.png" 2>/dev/null \
        && [[ -s $WORK_DIR/art.png ]] \
        && mv -f -- "$WORK_DIR/art.png" "$art_file"; then
        [[ -z $failure_file ]] || rm -f -- "$failure_file"
        if [[ -n ${stamp_file:-} ]]; then
            printf '%s\n' "$source_stamp" > "$WORK_DIR/source_stamp"
            mv -f -- "$WORK_DIR/source_stamp" "$stamp_file"
        fi
        echo "$art_file"
    else
        fallback_artwork "$stale_art_file" "$failure_file"
    fi
}

if (( $# != 1 )); then
    usage
    exit 1
fi

case "$1" in
    --title)
        title=$(get_metadata "xesam:title")
        [[ -n $title ]] && escape_metadata "$title"
        ;;
    --arturl)
        get_artwork
        ;;
    --artist)
        artist=$(get_metadata "xesam:artist")
        [[ -n $artist ]] && printf ' %s\n' "$(escape_metadata "$artist")"
        ;;
    --length)
        length=$(get_metadata "mpris:length")
        if [[ $length =~ ^[0-9]+$ ]]; then
            awk -v duration="$length" 'BEGIN { printf " %.2f m\n", duration / 60000000 }'
        fi
        ;;
    --status)
        case "$(get_status)" in
            Playing) echo "" ;;
            Paused) echo "" ;;
            *) echo "" ;;
        esac
        ;;
    --album)
        album=$(get_metadata "xesam:album")
        if [[ -n $album ]]; then
            escape_metadata "$album"
        elif [[ -n $(get_status) ]]; then
            echo "No album"
        fi
        ;;
    --source)
        get_source_info
        ;;
    *)
        echo "Invalid option: $1" >&2
        usage >&2
        exit 1
        ;;
esac

exit 0
