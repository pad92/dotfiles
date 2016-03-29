check_d3() {
    curl -s http://eu.battle.net/d3/fr/status | grep -A 3 '<h3 class="category">Europe</h3>' | grep -q 'status-icon down'
    if [ $? -eq 0 ]; then
        echo 'srv down'
    else
        echo 'srv up'
    fi
}

check_android () {
    "curl -s https://developers.google.com/android/nexus/images | sed -e 's/<[^>]*>//g' | grep -B2 \"Android \" | sed -e 's/^[ \t]*//' | sed '/^$/d'" 
}

check_http () {
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
