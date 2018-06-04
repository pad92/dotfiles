pmad() {
    if [ -z "$1" ]; then
        echo 'Usage : pmad PORT USER [TUNNEL 80:127.0.0.1:80]'
    else
        SSH_BIN=`which ssh`
        SSH_IP='pmad'
        SSH_PORT="$1"
        SSH_CMD="$SSH_BIN -Y $SSH_IP -p $SSH_PORT"
        SSH_CMD="$SSH_CMD -l $2"
        if [ -n "$3" ]; then
            SSH_CMD="$SSH_CMD -L $3"
        fi
        $=SSH_CMD
    fi
}
pmad_push() {
    if [ -z "$2" ]; then
        echo 'Usage : pmad_push SSH_PUB PORT USER'
    else
        SSH_PUB=$1
        PORT=$2
        SSH_LOGIN=$3
        if [ -f "$SSH_PUB" ]; then
            IP='pmad'
            ssh-copy-id -p $PORT -i $SSH_PUB $SSH_LOGIN@$IP
        else
            echo "$SSH_PUB not found"
        fi
    fi
}
