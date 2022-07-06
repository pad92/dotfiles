rambox_update(){
    if [ -f /etc/os-release ]; then
        source /etc/os-release
    else
        echo '/etc/os-release not found, os unknow'
        exit 1
    fi

    rambox_CURRENT=$(rpm -aq | grep -i rambox | cut -d'-' -f2)
    rambox_LATEST=$(curl -Ls https://api.github.com/repos/saenzramiro/rambox/releases/latest)
    rambox_LATEST_VERSION=$(echo -e ${rambox_LATEST} | grep -m 1 '"name"'                          | cut -d '"' -f 4)
    rambox_RPM=$(echo -e ${rambox_LATEST}            | grep -E 'browser_download_url(.*)\.rpm'     | cut -d '"' -f 4 | grep x86_64)
    rambox_DEB=$(echo -e ${rambox_LATEST}            | grep -E 'browser_download_url(.*)\.deb'     | cut -d '"' -f 4 | grep amd64)

    if [ "${rambox_LATEST_VERSION}" != "${rambox_CURRENT}" ]; then
        echo "upgrade rambox ${rambox_CURRENT} to ${rambox_LATEST_VERSION}"

        case ${ID} in
            fedora|centos)
                pkill rambox
                if [[ $UID == 0 || $EUID == 0 ]]; then
                    dnf -y install --nogpgcheck ${rambox_RPM}
                else
                    sudo dnf -y install --nogpgcheck ${rambox_RPM}
                fi
                ;;
        esac
    else
        echo "Nothing to do, ${rambox_LATEST_VERSION} is the current version of rambox"
    fi
}
