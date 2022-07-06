http_check_d3() {
    curl -s http://eu.battle.net/d3/fr/status | grep -A 3 '<h3 class="category">Europe</h3>' | grep -q 'status-icon down'
    if [ $? -eq 0 ]; then
        echo 'srv down'
    else
        echo 'srv up'
    fi
}

http_check_android () {
    curl -s https://developers.google.com/android/nexus/images | sed -e 's/<[^>]*>//g' | grep -B2 \"Android \" | sed -e 's/^[ \t]*//' | sed '/^$/d'
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
        sleep 1
    done
}

http_time () {
    CURL_FORMAT='                  http_code:  %{http_code}\n            time_namelookup:  %{time_namelookup} ms\n               time_connect:  %{time_connect} ms\n            time_appconnect:  %{time_appconnect} ms\n           time_pretransfer:  %{time_pretransfer} ms\n              time_redirect:  %{time_redirect} ms\n         time_starttransfer:  %{time_starttransfer} ms\n                            ----------\n                 time_total:  %{time_total} ms\n'
    curl -w "$CURL_FORMAT" -o /dev/null -s $1
}
