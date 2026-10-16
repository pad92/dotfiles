pmad() {
    if (( $# < 1 || $# > 3 )); then
        echo 'Usage : pmad [PORT] [USER] [TUNNEL 80:127.0.0.1:80]'
        return 2
    fi

    local ssh_bin
    ssh_bin=$(command -v ssh) || { echo 'ssh not found' >&2; return 127; }
    local -a ssh_args=(-Y -p "${1}")
    [[ -z "${2:-}" ]] || ssh_args+=(-l "$2")
    [[ -z "${3:-}" ]] || ssh_args+=(-L "$3")
    ssh_args+=(pmad)
    "$ssh_bin" "${ssh_args[@]}"
}
pmad_push() {
    if (( $# != 3 )) || [[ -z "$1" || -z "$2" || -z "$3" ]]; then
        echo 'Usage : pmad_push [SSH_PUB] [PORT] [USER]'
        return 2
    fi

    if [[ ! -f "$1" ]]; then
        echo "$1 not found" >&2
        return 1
    fi
    local ssh_copy_id
    ssh_copy_id=$(command -v ssh-copy-id) || {
        echo 'ssh-copy-id not found' >&2
        return 127
    }
    "$ssh_copy_id" -p "$2" -i "$1" "$3@pmad"
}
