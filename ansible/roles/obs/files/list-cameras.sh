#!/bin/sh
# Print "### <node>|<stable path>|<name>" then the v4l2-ctl format list for
# each V4L2 node. The stable path is a /dev/v4l/by-id link, else by-path.
set -eu
dev_root=${1:-/dev}
sys_root=${2:-/sys}
stable_path() {
    for dir in "$dev_root/v4l/by-id" "$dev_root/v4l/by-path"; do
        for link in "$dir"/*; do
            [ -L "$link" ] || continue
            if [ "$(readlink -f "$link")" = "$(readlink -f "$1")" ]; then
                printf '%s' "$link"
                return 0
            fi
        done
    done
}
for node in "$dev_root"/video[0-9]*; do
    [ -e "$node" ] || continue
    name=$(cat "$sys_root/class/video4linux/${node##*/}/name" 2>/dev/null || true)
    printf '### %s|%s|%s\n' "$node" "$(stable_path "$node")" "$name"
    v4l2-ctl --list-formats-ext -d "$node" 2>/dev/null || true
done
