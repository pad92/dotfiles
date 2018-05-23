meteo() {
    if [[ $# -eq 1 ]]; then
        curl -s "https://wttr.in/${1}"
    else
        curl -s 'https://wttr.in'
    fi
}
