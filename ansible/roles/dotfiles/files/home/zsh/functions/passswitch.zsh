####################################################################
##
##  This script help you manage switching between multiple
##  password-store.
##
##  it look into ~/.passswitch/ for files containing environment
##  var per password-store.
##
####################################################################

export PASSSWITCH_DIR="${HOME}/.passswitch"

_passswitch_cmd_help() {
    cat <<-_EOF
    Usage:
    passswitch [OPTIONS]
    passswitch <password-store>

    Options:
    -l  List defined password store
    -h  Show this help.
_EOF
}

_passswitch_cmd_list() {
    local store_file store
    while read -r -d "" store_file
    do
        store=${store_file##*/}
        store=${store%.conf}
        printf '\t%s\n' "$store"
    done < <(find "${PASSSWITCH_DIR}" -iname '*.conf' -print0 2>/dev/null)
}

_passswitch_cmd_switch() {
    if (( $# != 1 )) || [[ "$1" == *[!A-Za-z0-9_.-]* || "$1" == . || "$1" == .. ]]; then
        echo "Invalid password-store name" >&2
        return 2
    fi

    local store_file="${PASSSWITCH_DIR}/${1}.conf"
    if [[ ! -f "$store_file" ]]; then
        echo "Unknown password-store: $1" >&2
        return 1
    fi
    echo "switching to $1 password-store"
    source "$store_file"
}

passswitch() {
    if (( $# != 1 )); then
        _passswitch_cmd_help
        return 2
    fi

    case "$1" in
        -h|--help)  _passswitch_cmd_help;;
        -l|--list)  _passswitch_cmd_list;;
        *)          _passswitch_cmd_switch "$1";;
    esac
}
