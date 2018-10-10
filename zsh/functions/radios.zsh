radio(){
    if [ ${#} -ne 1 ]; then echo "usage: ${@} radio [radio name]"; fi

    fg='http://radiofg.impek.com/fg'

    case "${1}" in
        fg)
            cvlc http://radiofg.impek.com/fg
        ;;
        nova)
            cvlc http://broadcast.infomaniak.net/novazz-128.mp3 
        ;;
    esac
}
