crawler () {
    if [[ $# -eq 1 ]]; then
        SITEMAPS=$(curl -s $1 | xml2 | grep '/loc=' | sed 's/.*=//' 2>/dev/null)
        for URL in `echo $SITEMAPS`; do
            if [[ $URL =~ '\.xml$' ]]; then
                SITEMAPSS=$(curl -s $URL | xml2 | grep '/loc=' | sed 's/.*=//' 2>/dev/null)
                for URLS in `echo $SITEMAPSS`; do
                    HTTP_CODE=$(curl -s -w "%{http_code}" $URLS -o /dev/null 2>/dev/null)
                    echo "$HTTP_CODE - $URLS"
                done
            else
                HTTP_CODE=$(curl -s -w "%{http_code}" $URL -o /dev/null 2>/dev/null)
                echo "$HTTP_CODE - $URL"
            fi
        done

    else
        echo usage: crawler domain.ltd/sitemap.xml >&2
        return 1
    fi
}

