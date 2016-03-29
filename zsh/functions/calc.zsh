calc () {
    for exp in $argv; do
        print "$exp = $(( exp ))"
    done
}
