# Follow files and discover new matches every second; quote globs to keep watching them.
# Usage: mtail [file-or-pattern ...] (default: '*.log')
mtail() (
    emulate -L zsh
    setopt nullglob no_monitor

    local dependency
    for dependency in tail awk mktemp mkfifo; do
        if ! command -v "$dependency" >/dev/null 2>&1; then
            print -u2 -- "mtail: $dependency is required"
            return 127
        fi
    done

    local -a patterns pids
    patterns=("$@")
    (( ${#patterns} )) || patterns=('*.log')
    local -A followed
    local tmpdir pattern file fifo
    local -i next_fifo=0

    tmpdir=$(command mktemp -d "${TMPDIR:-/tmp}/mtail.XXXXXX") || return 1

    cleanup() {
        trap '' INT TERM HUP
        if (( ${#pids} )); then
            kill -- "${pids[@]}" 2>/dev/null
            wait "${pids[@]}" 2>/dev/null
        fi
        command rm -rf -- "$tmpdir"
    }
    trap cleanup EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    trap 'exit 129' HUP

    while true; do
        for pattern in "${patterns[@]}"; do
            for file in ${~pattern}; do
                # Use the same absolute path for literal, relative and overlapping matches.
                file=${file:a}
                [[ -f $file && -z ${followed[$file]} ]] || continue

                fifo="$tmpdir/fifo-$((next_fifo++))"
                command mkfifo -- "$fifo" || exit 1

                # Pass the prefix through the environment so awk preserves backslashes.
                MTAIL_PREFIX="${file:t}: " command awk \
                    '{ print ENVIRON["MTAIL_PREFIX"] $0; fflush() }' "$fifo" &
                pids+=($!)
                command tail -F -- "$file" >"$fifo" &
                pids+=($!)
                followed[$file]=1
            done
        done
        command sleep 1
    done
)
