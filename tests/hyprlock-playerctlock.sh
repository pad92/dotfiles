#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
PLAYER_HELPER=${PLAYER_HELPER:-"$ROOT_DIR/ansible/roles/dotfiles/files/home/.config/hypr/hyprlock/playerctlock.sh"}
EMPTY_IMAGE="$ROOT_DIR/ansible/roles/dotfiles/files/home/.config/hypr/hyprlock/empty.png"
TEST_DIR=$(mktemp -d)
trap 'rm -rf -- "$TEST_DIR"' EXIT

mkdir -p "$TEST_DIR/bin" "$TEST_DIR/runtime"
# Fills the --format template like playerctl and counts the calls.
cat > "$TEST_DIR/bin/playerctl" <<'EOF'
#!/bin/bash

printf 'call\n' >> "$MOCK_PLAYERCTL_LOG"
[[ $1 == metadata && $2 == --format ]] || exit 1
template=$3
declare -A values=(
    [playerName]=firefox [status]=Playing [xesam:title]="${MOCK_TITLE:-Song}"
    [xesam:artist]=Artist [xesam:album]="" [xesam:url]=https://www.deezer.com/track/1
    [mpris:artUrl]="${MOCK_ART_URL:-}" [mpris:length]=180000000
)
for key in "${!values[@]}"; do
    template=${template//"{{ $key }}"/"${values[$key]}"}
done
printf '%s\n' "$template"
EOF
chmod +x "$TEST_DIR/bin/playerctl"

export PATH="$TEST_DIR/bin:$PATH"
export XDG_RUNTIME_DIR="$TEST_DIR/runtime"
export MOCK_PLAYERCTL_LOG="$TEST_DIR/playerctl.log"
SNAPSHOT="$XDG_RUNTIME_DIR/hyprlock-mpris/metadata"

fail()
{
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

# Labels of one hyprlock update share a single playerctl call.
export MOCK_TITLE=$'Tab\tand <b>'
: > "$MOCK_PLAYERCTL_LOG"
title=$($PLAYER_HELPER --title)
artist=$($PLAYER_HELPER --artist)
status=$($PLAYER_HELPER --status)
source=$($PLAYER_HELPER --source)
album=$($PLAYER_HELPER --album)
[[ $(wc -l < "$MOCK_PLAYERCTL_LOG") -eq 1 ]] \
    || fail "the labels did not share one playerctl snapshot"
[[ $title == "Tab and &lt;b&gt;" ]] || fail "unexpected title: $title"
[[ $artist == *" Artist" ]] || fail "unexpected artist: $artist"
[[ -n $status ]] || fail "a playing player showed no status icon"
[[ $source == Deezer* ]] || fail "unexpected source: $source"
[[ $album == "No album" ]] || fail "unexpected album: $album"

# An old snapshot is refreshed.
touch -d '1 minute ago' "$SNAPSHOT"
export MOCK_TITLE=Next
[[ $($PLAYER_HELPER --title) == Next ]] || fail "a stale snapshot was reused"
[[ $(wc -l < "$MOCK_PLAYERCTL_LOG") -eq 2 ]] || fail "a stale snapshot did not query playerctl"

# The artwork steps below change the URL between calls: drop the snapshot first.
PLAYER_HELPER_ART()
{
    rm -f -- "$SNAPSHOT"
    $PLAYER_HELPER --arturl
}

cp "$EMPTY_IMAGE" "$TEST_DIR/source.png"
export MOCK_ART_URL="file://$TEST_DIR/source.png"
first_cover=$(PLAYER_HELPER_ART)
[[ $first_cover != "$EMPTY_IMAGE" && -s $first_cover ]] || fail "temporary artwork was not cached"

rm "$TEST_DIR/source.png"
second_cover=$(PLAYER_HELPER_ART)
[[ $second_cover == "$first_cover" ]] \
    || fail "cached artwork was not reused after the source disappeared"
[[ -s $second_cover ]] \
    || fail "the cached artwork disappeared with its temporary source"

cp "$EMPTY_IMAGE" "$TEST_DIR/source cover.png"
export MOCK_ART_URL="file://$TEST_DIR/source%20cover.png"
spaced_path_cover=$(PLAYER_HELPER_ART)
[[ $spaced_path_cover != "$EMPTY_IMAGE" && -s $spaced_path_cover ]] \
    || fail "a percent-encoded space in a local artwork URL was not decoded"

export MOCK_ART_URL=""
no_url_cover=$(PLAYER_HELPER_ART)
[[ $no_url_cover == "$EMPTY_IMAGE" ]] \
    || fail "an empty artwork URL did not return the transparent image"

export MOCK_ART_URL="file://$TEST_DIR/missing.png"
changed_url_cover=$(PLAYER_HELPER_ART)
[[ $changed_url_cover == "$EMPTY_IMAGE" ]] \
    || fail "a new missing artwork URL reused an unrelated cached cover"

cp "$EMPTY_IMAGE" "$TEST_DIR/source.png"
export MOCK_ART_URL="file://$TEST_DIR/source.png"
touch "$TEST_DIR/source.png"
cat > "$TEST_DIR/bin/magick" <<'EOF'
#!/bin/sh
printf 'called\n' > "$MOCK_MAGICK_MARKER"
exit 1
EOF
chmod +x "$TEST_DIR/bin/magick"
export MOCK_MAGICK_MARKER="$TEST_DIR/magick-called"
failed_refresh_cover=$(PLAYER_HELPER_ART)
[[ -s $MOCK_MAGICK_MARKER ]] \
    || fail "changed same-URL artwork did not trigger a conversion attempt"
[[ $failed_refresh_cover == "$first_cover" ]] \
    || fail "a failed refresh replaced the valid same-URL cache"
[[ -s $first_cover ]] || fail "a failed refresh damaged the cached artwork"

printf 'PASS: hyprlock temporary artwork cache\n'
