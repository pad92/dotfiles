#atom_update(){
    ATOM_LATEST=`curl -w "%{url_effective}\n" -I -L -s -S https://github.com/atom/atom/releases/latest -o /dev/null | awk -F '/' '{print $NF}' | sed 's/v//'`
    ATOM_CURRENT=`atom -v | grep '^Atom' | awk '{print $NF}' 2>/dev/null`

    if [ "${ATOM_LATEST}" != "${ATOM_CURRENT}" ]; then
        echo upgrade atom ${ATOM_CURRENT} to ${ATOM_LATEST}
        RPM_LATEST=`curl -s https://api.github.com/repos/atom/atom/releases/latest | grep -E "${ATOM_LATEST}\/(.*)\.rpm" | cut -d '"' -f 4`
        if [[ $UID == 0 || $EUID == 0 ]]; then
            dnf install --nogpgcheck ${RPM_LATEST}
        else
            sudo dnf install --nogpgcheck ${RPM_LATEST}
        fi
    fi
#}
