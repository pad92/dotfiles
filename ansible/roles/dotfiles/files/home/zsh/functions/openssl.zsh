# OpenSSL
alias openssl_s_client_date='f() { openssl s_client -connect $1:443 </dev/null | openssl x509 -noout -dates };f'
