md5()    { echo -n $1 | openssl md5 /dev/stdin }
sha1()   { echo -n $1 | openssl sha1 /dev/stdin }
sha256() { echo -n $1 | openssl dgst -sha256 /dev/stdin }
sha512() { echo -n $1 | openssl dgst -sha512 /dev/stdin }

urlencode() { python -c "import sys, urllib as ul; print ul.quote_plus(sys.argv[1])" "$@" }
urldecode() { python -c "import sys, urllib as ul; print ul.unquote_plus(sys.argv[1])" "$@" }
