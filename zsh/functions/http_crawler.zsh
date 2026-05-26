http_crawler () {
    BIN_DEPS='curl grep sed'
    # === CHECKS ===
    for BIN in `echo $BIN_DEPS`; do
        which $BIN 1>/dev/null 2>&1
        if [ $? -ne 0 ]; then
            echo "Error: Required binary could not be found: $BIN"
            return 1
        fi
    done

    if [[ $# -eq 1 ]]; then
        # Extract all <loc> tags and remove the tags themselves
        local SITEMAPS_LIST=$(curl -sL "$1" | grep -o '<loc>[^<]*</loc>' | sed 's/<\/\?loc>//g')

        # Use Zsh line splitting (f) to iterate over each URL
        for URL in ${(f)SITEMAPS_LIST}; do
            [[ -z "$URL" ]] && continue
            if [[ $URL =~ '\.xml$' ]]; then
                http_crawler "$URL"
            else
                HTTP_CODE=$(curl -s -w "%{http_code}" "$URL" -o /dev/null -L 2>/dev/null)
                echo "$HTTP_CODE - $URL"
            fi
        done
        return 0

    else
        echo usage: crawler domain.ltd/sitemap.xml >&2
        return 1
    fi
}
