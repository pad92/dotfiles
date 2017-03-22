exquilla_gen () {
    if [ "$#" -ne 1 ] ; then
        echo "Usage: $0 user@domain.ltd" >&2
    else
        MAIL_ADDRESS=$1
        DATE_EXPIRE=`date +%Y-%m-%d -d "1 year"`
        LICENCE_MD5=`echo -n "EX1,$1,$DATE_EXPIRE,356B4B5C" | md5sum | cut -d' ' -f1`
        echo "EX1,$1,$DATE_EXPIRE,$LICENCE_MD5"
    fi
}
