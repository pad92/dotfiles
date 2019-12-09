pmad() {
    if [ -z "$1" ]; then
        echo 'Usage : pmad [PORT] [USER] [TUNNEL 80:127.0.0.1:80]'
    else
        SSH_PORT="${1}"
        SSH_USER="${2}"
        SSH_TUNNEL="${3}"
        SSH_BIN=$(command -v ssh)
        SSH_IP='pmad'                           # add pmad into /etc/hosts ;)
        SSH_CMD="${SSH_BIN} -Y ${SSH_IP} -p ${SSH_PORT}"
        if [ -x "${SSH_BIN}" ]; then
            if [ -n "${SSH_USER}" ]; then
                SSH_CMD="${SSH_CMD} -l ${SSH_USER}"
            fi
            if [ -n "$SSH_TUNNEL" ]; then
                SSH_CMD="${SSH_CMD} -L ${SSH_TUNNEL}"
            fi
            $=SSH_CMD
        else
            echo 'ssh not found'
        fi
    fi
}
pmad_push() {
    if [ -z "$1" ]; then
        echo 'Usage : pmad_push [SSH_PUB] [PORT] [USER]'
    else
        SSH_PUB="${1}"
        PORT="${2}"
        SSH_LOGIN="${3}"
        SSH_BIN="$(command -v ssh-copy-id)"
        if [ -x "${SSH_BIN}" ]; then
            if [ -f "$SSH_PUB" ]; then
                IP='pmad'
                "${SSH_BIN}" -p "${PORT}" -i "${SSH_PUB}" "${SSH_LOGIN}@${IP}"
            else
                echo "${SSH_PUB} not found"
            fi
        else
            echo 'ssh-copy-id not found'
        fi
    fi
}
