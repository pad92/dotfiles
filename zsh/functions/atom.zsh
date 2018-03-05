atom_update(){
    if [ -f /etc/os-release ]; then
        source /etc/os-release
    else
        echo '/etc/os-release not found, os unknow'
        exit 1
    fi

    ATOM_CURRENT=`atom -v | grep '^Atom' | awk '{print $NF}' 2>/dev/null`
    ATOM_LATEST=$(curl -s https://api.github.com/repos/atom/atom/releases/latest)
    ATOM_LATEST_VERSION=$(echo ${ATOM_LATEST} | grep -m 1 '"name"'                          | cut -d '"' -f 4)
    ATOM_RPM=$(echo ${ATOM_LATEST}            | grep -E 'browser_download_url(.*)\.rpm'     | cut -d '"' -f 4)
    ATOM_DEB=$(echo ${ATOM_LATEST}            | grep -E 'browser_download_url(.*)\.deb'     | cut -d '"' -f 4)

    if [ "${ATOM_LATEST_VERSION}" != "${ATOM_CURRENT}" ]; then
        echo "upgrade atom ${ATOM_CURRENT} to ${ATOM_LATEST_VERSION}"

        case ${ID} in
            fedora|centos) 
                if [[ $UID == 0 || $EUID == 0 ]]; then
                    dnf -y install --nogpgcheck ${ATOM_RPM}
                else
                    sudo dnf -y install --nogpgcheck ${ATOM_RPM}
                fi
                ;;
            ubuntu|debian)
                if [[ $UID == 0 || $EUID == 0 ]]; then
                    dpkg -i ${ATOM_DEB}
                else
                    sudo dpkg -i ${ATOM_DEB}
                fi
                ;;
        esac
    else
        echo "Nothing to do, ${ATOM_LATEST_VERSION} is the current version of Atom"
    fi
}
