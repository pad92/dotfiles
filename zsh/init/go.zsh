GOPATH=$HOME/.go

if [ ! -d  "$GOPATH" ]; then
    mkdir -p $GOPATH
fi

export GOPATH=$GOPATH
