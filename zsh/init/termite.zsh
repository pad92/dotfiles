# allow termite to open new tabs on current directory
if [[ "${TERM}" == "xterm-termite" ]]; then
    if [[ -f "/etc/profile.d/vte.sh" ]]; then
        source /etc/profile.d/vte.sh
        __vte_osc7
    fi
fi
