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
ART_FILE="$ART_DIR/mpris_artUrl"
RESIZED_ART_FILE="$ART_DIR/mpris_artUrl_resized"

# Function to get metadata using playerctl
get_metadata()
{
    key=$1
    playerctl metadata --format "{{ $key }}" 2> /dev/null
}

# Function to determine the source and return an icon and text
get_source_info()
{
    trackid=$(get_metadata "mpris:trackid")
    if [[ "$trackid" == *"firefox"* ]]; then
        echo -e "Firefox "
    elif [[ "$trackid" == *"spotify"* ]]; then
        echo -e "Spotify "
    elif [[ "$trackid" == *"chromium"* ]]; then
        echo -e "Chrome "
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
        url=$(get_metadata "mpris:artUrl")
        if [ -z "$url" ]; then
            echo ""
            [ -f "$ART_FILE" ] && rm -f "$ART_FILE"
            [ -f "$RESIZED_ART_FILE" ] && rm -f "$RESIZED_ART_FILE"
        else
            if [[ "$url" == file://* ]]; then
                url=${url#file://}
            elif [[ "$url" == https://* ]]; then
                if curl -fsSL --max-time 5 "${url}" -o "$ART_FILE"; then
                    url="$ART_FILE"
                else
                    echo ""
                    exit 0
                fi
            fi

            # Resize image to fit hyprlock display requirements (110px smallest dimension)
            if command -v convert >/dev/null 2>&1; then
                convert "$url" -resize 110x110^ -gravity center -crop 110x110+0+0 "$RESIZED_ART_FILE" 2>/dev/null && url="$RESIZED_ART_FILE"
            fi

            echo "$url"
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
