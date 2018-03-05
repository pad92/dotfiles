atom_update(){
    if [ -f /etc/os-release ]; then
        source /etc/os-release
    else
        echo '/etc/os-release not found, os unknow'
        exit 1
    fi

    ATOM_LATEST=`curl -w "%{url_effective}\n" -I -L -s -S https://github.com/atom/atom/releases/latest -o /dev/null | awk -F '/' '{print $NF}' | sed 's/v//'`
    ATOM_CURRENT=`atom -v | grep '^Atom' | awk '{print $NF}' 2>/dev/null`

    if [ "${ATOM_LATEST}" != "${ATOM_CURRENT}" ]; then
        echo upgrade atom ${ATOM_CURRENT} to ${ATOM_LATEST}

        case ${ID} in
            fedora|centos)
                RPM_LATEST=`curl -s https://api.github.com/repos/atom/atom/releases/latest | grep -E "${ATOM_LATEST}\/(.*)\.rpm" | cut -d '"' -f 4`
                if [[ $UID == 0 || $EUID == 0 ]]; then
                    dnf -y install --nogpgcheck ${RPM_LATEST}
                else
                    sudo dnf -y install --nogpgcheck ${RPM_LATEST}
                fi
                ;;
            ubuntu|debian)
                DEB_LATEST=`curl -s https://api.github.com/repos/atom/atom/releases/latest | grep -E "${ATOM_LATEST}\/(.*)\.deb" | cut -d '"' -f 4`
                if [[ $UID == 0 || $EUID == 0 ]]; then
                    dpkg -i ${DEB_LATEST}
                else
                    sudo dpkg -i ${DEB_LATEST}
                fi
                ;;
        esac
    fi
}
