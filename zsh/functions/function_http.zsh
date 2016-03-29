ip_p () {
    echo -n "Current External IP: "
    curl -s -m 5 http://myip.dk | grep "ha4" | sed -e 's/.*ha4">//g' -e 's/<\/span>.*//g'
}

ip_l () {
    echo -n "Current Local IP: "
    ifconfig | grep "inet " | awk '{ print $2 }'
}

http_check () {
    echo "GET $@"
    echo "press ^C to stop"
    while true; do
        HTTP_VALUE=$(curl -s -I $@ | grep ^HTTP | awk '{ print $2}')
        if [ "$HTTP_VALUE" -eq "200" ]; then
            echo -n .
        else
            echo " $HTTP_VALUE "
        fi
    done
}
