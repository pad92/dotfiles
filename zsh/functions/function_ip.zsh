ip_p () {
    echo -n "Current External IP: "
    curl -s -m 5 http://myip.dk | grep "ha4" | sed -e 's/.*ha4">//g' -e 's/<\/span>.*//g'
}

ip_l () {
    echo -n "Current Local IP: "
    ifconfig | grep "inet " | awk '{ print $2 }'
}
