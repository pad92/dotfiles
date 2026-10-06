#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
PLAYER_HELPER=${PLAYER_HELPER:-"$ROOT_DIR/.config/hypr/hyprlock/playerctlock.sh"}
EMPTY_IMAGE="$ROOT_DIR/.config/hypr/hyprlock/empty.png"
TEST_DIR=$(mktemp -d)
trap 'rm -rf -- "$TEST_DIR"' EXIT

mkdir -p "$TEST_DIR/bin" "$TEST_DIR/runtime"
cat > "$TEST_DIR/bin/playerctl" <<'EOF'
#!/bin/sh

case "$*" in
    *mpris:artUrl*) printf '%s\n' "${MOCK_ART_URL:-}" ;;
    *) exit 1 ;;
esac
EOF
chmod +x "$TEST_DIR/bin/playerctl"

export PATH="$TEST_DIR/bin:/usr/bin"
export XDG_RUNTIME_DIR="$TEST_DIR/runtime"

fail()
{
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

cp "$EMPTY_IMAGE" "$TEST_DIR/source.png"
export MOCK_ART_URL="file://$TEST_DIR/source.png"
first_cover=$($PLAYER_HELPER --arturl)
[[ -s $first_cover ]] || fail "temporary artwork was not cached"

rm "$TEST_DIR/source.png"
second_cover=$($PLAYER_HELPER --arturl)
[[ $second_cover == "$first_cover" ]] \
    || fail "cached artwork was not reused after the source disappeared"
[[ -s $second_cover ]] \
    || fail "the cached artwork disappeared with its temporary source"

cp "$EMPTY_IMAGE" "$TEST_DIR/source cover.png"
export MOCK_ART_URL="file://$TEST_DIR/source%20cover.png"
spaced_path_cover=$($PLAYER_HELPER --arturl)
[[ $spaced_path_cover != "$EMPTY_IMAGE" && -s $spaced_path_cover ]] \
    || fail "a percent-encoded space in a local artwork URL was not decoded"

export MOCK_ART_URL=""
no_url_cover=$($PLAYER_HELPER --arturl)
[[ $no_url_cover == "$EMPTY_IMAGE" ]] \
    || fail "an empty artwork URL did not return the transparent image"

export MOCK_ART_URL="file://$TEST_DIR/missing.png"
changed_url_cover=$($PLAYER_HELPER --arturl)
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
failed_refresh_cover=$($PLAYER_HELPER --arturl)
[[ -s $MOCK_MAGICK_MARKER ]] \
    || fail "changed same-URL artwork did not trigger a conversion attempt"
[[ $failed_refresh_cover == "$first_cover" ]] \
    || fail "a failed refresh replaced the valid same-URL cache"
[[ -s $first_cover ]] || fail "a failed refresh damaged the cached artwork"

printf 'PASS: hyprlock temporary artwork cache\n'
