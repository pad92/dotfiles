http_crawler () {
    BIN_DEPS='xml2 curl'
    # === CHECKS ===
    for BIN in `echo $BIN_DEPS`; do
        which $BIN 1>/dev/null 2>&1
        if [ $? -ne 0 ]; then
            echo "Error: Required binarie could not be found: $BIN"
            return 1
        fi
    done

    if [[ $# -eq 1 ]]; then
        SITEMAPS=$(curl -s $1 -L | xml2 | grep '/loc=' | sed 's/.*=//' 2>/dev/null)
        for URL in `echo $SITEMAPS`; do
            if [[ $URL =~ '\.xml$' ]]; then
                http_crawler $URL
            else
                HTTP_CODE=$(curl -s -w "%{http_code}" $URL -o /dev/null -L 2>/dev/null)
                echo "$HTTP_CODE - $URL"
            fi
        done
        return 0

    else
        echo usage: crawler domain.ltd/sitemap.xml >&2
        return 1
    fi
}
