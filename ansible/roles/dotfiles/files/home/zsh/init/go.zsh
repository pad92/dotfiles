if [ -d "${HOME}/.go" ]; then
    export GOPATH=${HOME}/.go
    if [ -d "${HOME}/.go/bin" ]; then
        export PATH="${PATH}:${HOME}/.go/bin"
    fi
fi
