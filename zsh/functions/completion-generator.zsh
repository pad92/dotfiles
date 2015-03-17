# Parse getopt-style help texts for options
# and generate zsh(1) completion functions.
# http://github.com/RobSis/zsh-completion-generator

OUTPUTDIR="${ZSH}completions"
SCRIPTDIR="${ZSH}scripts"

function gencomp() {
    if [ -z "$1" ]; then
        echo "Usage: gencomp program [--argument-for-help-text]"
        echo
        return 1
    fi

    help=--help
    if [ -n "$2" ]; then
        help=$2
    fi

    $1 $help 2>&1 | /usr/bin/python $SCRIPTDIR/help2comp.py $1 > $OUTPUTDIR/_$1 || ( rm -f $OUTPUTDIR/_$1 &&\
        echo "No options found for '$1'." )
}
