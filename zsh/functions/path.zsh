path() {
  echo $PATH | tr ":" "\n" | \
    awk "{ sub(\"/usr\",   \"$fg_no_bold[green]/usr$reset_color\"); \
           sub(\"/bin\",   \"$fg_bold[blue]/bin$reset_color\"); \
           sub(\"/sbin\",  \"$fg_bold[magenta]/sbin$reset_color\"); \
           sub(\"/local\", \"$fg_no_bold[yellow]/local$reset_color\"); \
           sub(\"/opt\",   \"$fg_no_bold[cyan]/opt$reset_color\"); \
           sub(\"/home\",  \"$fg_no_bold[red]/home$reset_color\"); \
           print }"
}

ANDROID_PATH=`realpath ~/Android/Sdk/platform-tools`

if [ -d "$ANDROID_PATH" ]; then
    export PATH=$PATH":$ANDROID_PATH"
fi
