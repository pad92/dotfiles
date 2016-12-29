curl_time() {
    CURL_FORMAT='                  http_code:  %{http_code}
            time_namelookup:  %{time_namelookup} ms
               time_connect:  %{time_connect} ms
            time_appconnect:  %{time_appconnect} ms
           time_pretransfer:  %{time_pretransfer} ms
              time_redirect:  %{time_redirect} ms
         time_starttransfer:  %{time_starttransfer} ms
                            ----------
                 time_total:  %{time_total} ms\n'

	curl -w "$CURL_FORMAT" -o /dev/null -s $1
}
