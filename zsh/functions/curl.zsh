curl_time() {
    CURL_FORMAT='                  http_code:  %{http_code}
            time_namelookup:  %{time_namelookup}s
               time_connect:  %{time_connect}s
            time_appconnect:  %{time_appconnect}s
           time_pretransfer:  %{time_pretransfer}s
              time_redirect:  %{time_redirect}s
         time_starttransfer:  %{time_starttransfer}s
                            ----------
                 time_total:  %{time_total}s\n'

	curl -w "$CURL_FORMAT" -o /dev/null -s $1
}
