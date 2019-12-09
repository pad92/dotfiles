radio(){
    if [ ${#} -ne 1 ]; then
        echo "usage: ${@} radio [radio name]"
    fi

RADIO_FG='http://radiofg.impek.com/fg.mp3'
RADIO_NOVA='http://novazz.ice.infomaniak.ch/novazz-128.mp3'

case "${1}" in
    fg)
        cvlc "${RADIO_FG}"
    ;;
    nova)
        cvlc "${RADIO_NOVA}"
    ;;
esac
}
