if [ -d "$HOME/.go" ]; then
    export GOPATH=$HOME/.go
    if [ -d "$HOME/.go/bin" ]; then
        export PATH="$HOME/.go/bin:$PATH"
    fi
fi
