updatedebian () {
    if [[ $UID == 0 || $EUID == 0 ]]; then
        apt-get update
        apt-get upgrade
        apt-get dist-upgrade
        apt-get clean
        apt-get autoclean
        apt-get autoremove
    else
        sudo apt-get update
        sudo apt-get upgrade
        sudo apt-get dist-upgrade
        sudo apt-get clean
        sudo apt-get autoclean
        sudo apt-get autoremove
    fi
}
