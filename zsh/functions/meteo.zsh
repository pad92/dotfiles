meteo() {
    IP_GW=$(ip route show default 0.0.0.0/0 | head -1 | cut -d' ' -f 3)
    IP_PUB=$(dig -4 TXT +short o-o.myaddr.l.google.com @${IP_GW})

    if [[ $# -eq 1 ]]; then
        curl -s "https://wttr.in/${1}"
    else
        curl -s 'https://wttr.in'
    fi
}
