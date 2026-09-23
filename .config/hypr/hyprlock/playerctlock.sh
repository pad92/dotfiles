#!/usr/bin/env bash

if [ $# -eq 0 ]; then
    echo "Usage: $0 --title | --arturl | --artist | --length | --album | --source"
    exit 1
fi

if [ -n "${XDG_RUNTIME_DIR:-}" ]; then
    ART_DIR="$XDG_RUNTIME_DIR"
else
    ART_DIR="${TMPDIR:-/tmp}/hyprlock-mpris-${UID:-$(id -u)}"
    mkdir -p "$ART_DIR"
    chmod 700 "$ART_DIR"
fi


# Function to get metadata using playerctl
get_metadata()
{
    key=$1
    playerctl metadata --format "{{ $key }}" 2> /dev/null
}

# Function to determine the source and return an icon and text
get_source_info()
{
    player_name=$(get_metadata "playerName")
    if [[ "$player_name" == *"firefox"* ]]; then
        echo -e "Firefox  "
    elif [[ "$player_name" == *"spotify"* ]]; then
        echo -e "Spotify  "
    elif [[ "$player_name" == *"chromium"* ]]; then
        echo -e "Chrome  "
    else
        echo ""
    fi
}

# Parse the argument
case "$1" in
    --title)
        title=$(get_metadata "xesam:title")
        if [ -z "$title" ]; then
            echo ""
        else
            echo "${title}"
        fi
        ;;
    --arturl)
        empty_file="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/empty.png"
        url=$(get_metadata "mpris:artUrl") || url=""
        if [ -z "$url" ]; then
            echo "$empty_file"
            exit 0
        fi

        # A URL-specific filename keeps concurrent requests from mixing cache entries.
        cache_key=$(printf '%s' "$url" | sha256sum) || { echo "$empty_file"; exit 0; }
        art_file="$ART_DIR/mpris_artUrl_${cache_key%% *}.png"
        if [ -s "$art_file" ]; then
            echo "$art_file"
            exit 0
        fi

        work_dir=$(mktemp -d "$ART_DIR/mpris_artUrl.XXXXXXXXXX") || { echo "$empty_file"; exit 0; }
        trap 'rm -rf -- "$work_dir"' EXIT
        trap 'exit 1' HUP INT TERM
        if [[ "$url" == file://* ]]; then
            url=${url#file://}
        elif [[ "$url" == https://* || "$url" == http://* ]]; then
            if ! curl -fsSL --max-time 5 "$url" -o "$work_dir/download"; then
                echo "$empty_file"
                exit 0
            fi
            url="$work_dir/download"
        fi

        if command -v magick >/dev/null 2>&1; then
            converter=magick
        elif command -v convert >/dev/null 2>&1; then
            converter=convert
        else
            echo "$empty_file"
            exit 0
        fi

        # Only publish complete ONGs; temporary files stay on the same filesystem.
        if "$converter" "$url" -resize 150x150^ -gravity center -crop 150x150+0+0 +repage "PNG:$work_dir/art.png" 2>/dev/null \
            && [ -s "$work_dir/art.png" ] \
            && mv -f -- "$work_dir/art.png" "$art_file"; then
            echo "$art_file"
        else
            echo "$empty_file"
        fi
        ;;
    --artist)
        artist=$(get_metadata "xesam:artist")
        if [ -z "$artist" ]; then
            echo ""
        else
            echo " ${artist}"
        fi
        ;;
    --length)
        length=$(get_metadata "mpris:length")
        if [ -z "$length" ]; then
            echo ""
        else
            # Convert length from microseconds to a more readable format (seconds)
            echo " $(echo "scale=2; $length / 1000000 / 60" | bc) m"
        fi
        ;;
    --status)
        status=$(playerctl status 2> /dev/null)
        if [[ $status == "Playing" ]]; then
            echo ""
        elif [[ $status == "Paused" ]]; then
            echo ""
        else
            echo ""
        fi
        ;;
    --album)
        album=$(playerctl metadata --format "{{ xesam:album }}" 2> /dev/null)
        if [[ -n $album ]]; then
            echo "$album"
        else
            status=$(playerctl status 2> /dev/null)
            if [[ -n $status ]]; then
                echo "No album"
            else
                echo ""
            fi
        fi
        ;;
    --source)
        get_source_info
        ;;
    *)
        echo "Invalid option: $1"
        echo "Usage: $0 --title | --arturl | --artist | --length | --album | --source"
        exit 1
        ;;
esac
