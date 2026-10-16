## smart urls
autoload -U url-quote-magic
zle -N self-insert url-quote-magic

## jobs
setopt LONG_LIST_JOBS
