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
    fi
    return 0
}

## youtube-dl
if [ $(command -v youtube-dl) ]; then
  function yta() {
    local format="$1"
    shift
    youtube-dl --extract-audio --audio-format "$format" "$@"
  }

  alias yta-aac="yta aac"
  alias yta-best="yta best"
  alias yta-flac="yta flac"
  alias yta-m4a="yta m4a"
  alias yta-mp3="yta mp3"
  alias yta-opus="yta opus"
  alias yta-vorbis="yta vorbis"
  alias yta-wav="yta wav"
  alias ytv-best="youtube-dl -f bestvideo+bestaudio"
fi
