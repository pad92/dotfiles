#!/bin/bash

####################################################################
##
##  This script help you manage switching beetween multiple
##  password-store.
##
##  it look into ~/.passswitch/ for files containing environnement
##  var per password-store.
##
####################################################################

export PASSSWITCH_DIR=${HOME}/.passswitch

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
    while read -r -d "" STOREFILE
    do
        STORE=${STOREFILE%%.conf}
        STORE=${STORE##*/}
        echo -e "\t${STORE}"
    done < <(find "${PASSSWITCH_DIR}" -iname '*.conf' -print0 2>/dev/null)
}

_passswitch_cmd_switch() {
    if [ -f "${PASSSWITCH_DIR}/${1}.conf" ]
    then
        echo "switching to ${1} password-store"
        . ${PASSSWITCH_DIR}/${1}.conf
    else
        echo "Unknown password-store" >&2
    fi
}

passswitch() {

    case "$1" in
        -h|--help)  _passswitch_cmd_help;;
        -l|--list)  _passswitch_cmd_list;;
        *)          _passswitch_cmd_switch $1;;
    esac
}
