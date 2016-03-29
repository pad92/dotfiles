youtubeEncode() {
    if [ ! -f "$1" ]; then
        echo "Usage : youtubeEncode file_2_encode.mov"
        return 2
    fi
    INPUT=$1
    OUTPUT=$(echo $INPUT | sed 's/ /_/g')
    OUTPUTFN=$(basename "$OUTPUT")
    OUTPUT_OK="${OUTPUTFN%.*}.mp4"

    if [ -f "$OUTPUT_OK" ]; then
        OUTPUT="tmp_$OUTPUT_OK"
        CLEAN="true"
    else
        OUTPUT=$OUTPUT_OK
        CLEAN="false"
    fi

    ffmpeg -i $INPUT -c:v libx264 -preset slow -crf 25 -pix_fmt yuv420p $OUTPUT || return 1

    if [[ "$CLEAN" == "true" ]]; then
         mv $OUTPUT $OUTPUT_OK
     else
         rm $INPUT
    fi
    return 0
}
