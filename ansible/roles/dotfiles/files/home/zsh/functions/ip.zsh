ip_p () {
    echo -n "Current External IP:\t"
    dig +short myip.opendns.com @resolver1.opendns.com
}

ip_l () {
    echo -n "Current Local IP:\t"
    /sbin/ip addr show | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p'
}

ip_a () {
    ip_p
    ip_l
}
