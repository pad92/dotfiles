transfer() {
    # write to output to tmpfile because of progress bar
    tmpfile=$( mktemp -t transferXXX )
    curl --progress-bar --upload-file $1 https://transfer.sh/$(basename $1) >> $tmpfile;
    URL=`cat $tmpfile`;
    echo $URL
    echo $URL >> ~/.transfer.log
    rm -f $tmpfile;
}
