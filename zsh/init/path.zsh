addExportPath()
{
    if [ -d "$1" ] ; then
        if [ ! "$2" = "" -a -d "$2" ]; then
            export PATH="$2:$PATH"
        fi
        export PATH="$1:$PATH"
    fi
}

#addExportPath '/sbin'
#addExportPath '/usr/sbin'
#addExportPath '/usr/local/sbin'

if [ -d "$HOME/local/bin" ]; then
    export PATH="$HOME/local/bin:$PATH"
fi
