# Load and initialize the completion system ignoring insecure directories.
# Rebuild the dump (and run the security check) at most once a day; otherwise
# reuse the cached dump with -C to skip the slow per-startup scan.
zmodload zsh/complist
autoload -Uz compinit
# The (#q) glob qualifier needs extended_glob, which is off at this point.
# compinit only rewrites a changed dump, so touch it to restart the day.
_zcompdump=${ZDOTDIR:-${HOME}}/.zcompdump
if () { setopt localoptions extendedglob; [[ ! -s $_zcompdump || -n $_zcompdump(#qN.mh+24) ]] }; then
  compinit -i -d $_zcompdump
  touch $_zcompdump
else
  compinit -C -i -d $_zcompdump
fi
unset _zcompdump

setopt COMPLETE_IN_WORD # Complete from both ends of a word.
setopt ALWAYS_TO_END # Move cursor to the end of a completed word.
setopt PATH_DIRS # Perform path search even on command names with slashes.
setopt AUTO_MENU # Show completion menu on a successive tab press.
setopt AUTO_LIST # Automatically list choices on ambiguous completion.
setopt AUTO_PARAM_SLASH # If completed parameter is a directory, add a trailing slash.
unsetopt MENU_COMPLETE # Do not autoselect the first completion entry.
unsetopt FLOW_CONTROL # Disable start/stop characters in shell editor.

autoload -U colors
colors

# Treat these characters as part of a word.
WORDCHARS='*?_-.[]~&;!#$%^(){}<>'
#WORDCHARS=''

# Use caching to make completion for commands such as dpkg and apt usable.
zstyle ':completion:*' accept-exact '*(N)'
zstyle ':completion:*' use-cache on
zstyle ':completion:*' cache-path "${ZSH_CACHE_DIR}"

## case-insensitive (all),partial-word and then substring completion
if [ "x$CASE_SENSITIVE" = "xtrue" ]; then
  zstyle ':completion:*' matcher-list 'r:|[._-]=* r:|=*' 'l:|=* r:|=*'
  unset CASE_SENSITIVE
else
  zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}' 'r:|[._-]=* r:|=*' 'l:|=* r:|=*'
fi

zstyle ':completion:*' list-colors ''

# Group matches and describe.
zstyle ':completion:*:*:*:*:*' menu select
zstyle ':completion:*:matches' group 'yes'
zstyle ':completion:*:options' description 'yes'
zstyle ':completion:*:options' auto-description '%d'
zstyle ':completion:*:corrections' format " $fg[green]-- %d (errors: %e) --%f$reset_color"
zstyle ':completion:*:descriptions' format " $fg[yellow]-- %d --%f$reset_color"
zstyle ':completion:*:messages' format " $fg[purple] -- %d --%f$reset_color"
zstyle ':completion:*:warnings' format " $fg[red]-- no matches found --%f$reset_color"
zstyle ':completion:*:default' list-prompt '%S%M matches%s'
zstyle ':completion:*' format " $reset_color$fg[yellow]-- %d --%f$reset_color"
zstyle ':completion:*' group-name ''
zstyle ':completion:*' verbose yes

# Fuzzy match mistyped completions.
zstyle ':completion:*' completer _complete _match _approximate
zstyle ':completion:*:match:*' original only
zstyle ':completion:*:approximate:*' max-errors 1 numeric

# Increase the number of errors based on the length of the typed word.
zstyle -e ':completion:*:approximate:*' max-errors 'reply=($((($#PREFIX+$#SUFFIX)/3))numeric)'

# Don't complete unavailable commands.
zstyle ':completion:*:functions' ignored-patterns '(_*|pre(cmd|exec))'

# Array completion element sorting.
zstyle ':completion:*:*:-subscript-:*' tag-order indexes parameters

# Directories
zstyle ':completion:*:default' list-colors ${(s.:.)LS_COLORS}
zstyle ':completion:*:*:cd:*' tag-order local-directories directory-stack path-directories
zstyle ':completion:*:*:cd:*:directory-stack' menu yes select
zstyle ':completion:*:-tilde-:*' group-order 'named-directories' 'path-directories' 'users' 'expand'
zstyle ':completion:*' squeeze-slashes true
zstyle ':completion:*' special-dirs true

# History
zstyle ':completion:*:history-words' stop yes
zstyle ':completion:*:history-words' remove-all-dups yes
zstyle ':completion:*:history-words' list false
zstyle ':completion:*:history-words' menu yes

# Environmental Variables
zstyle ':completion::*:(-command-|export):*' fake-parameters ${${${_comps[(I)-value-*]#*,}%%,*}:#-*-}

# Host names for every command that completes hosts (ssh, scp, rsync, ping...).
# zsh only reads ~/.ssh/config for ssh, scp and sftp, so the `hosts` style
# gathers all sources, read again on each completion:
# - /etc/hosts (getent), names and IP addresses;
# - /etc/ssh/ssh_known_hosts and ~/.ssh/known_hosts: comma lists, [host]:port
#   and @cert-authority lines; @revoked lines and hashed entries are skipped;
# - ~/.ssh/config and the files it Includes (relative to ~/.ssh), Host and
#   Match host lines, keyword case and `=` as in ssh_config.
# Patterns (*, ?, %) and negations (!) are skipped.
_dotfiles_hosts() {
  emulate -L zsh -o extendedglob
  local -a hosts files names
  local file line key value name
  hosts=(${=${(f)"$(getent hosts 2>/dev/null)"}})
  for file in /etc/ssh/ssh_known_hosts(N) ~/.ssh/known_hosts(N); do
    for line in ${(f)"$(<$file)"}; do
      [[ $line == @revoked[[:space:]]* ]] && continue
      [[ $line == @* ]] && line=${line#* }
      [[ $line == (\#|\|)* ]] && continue
      for name in ${(s:,:)line%%[[:space:]]*}; do
        [[ $name == \[(#b)([^\]]#)\]:<-> ]] && name=$match[1]
        hosts+=($name)
      done
    done
  done
  files=(~/.ssh/config(N))
  local -i depth=0
  while (( $#files && depth++ < 16 )); do
    file=$files[1]; shift files
    for line in ${(f)"$(<$file)"}; do
      line=${line##[[:space:]]#}
      key=${line%%[[:space:]=]*} value=${${line#$key}##[[:space:]=]#}
      case ${(L)key} in
        include)
          files+=(${~${(z)value}/#(#m)[^\/~]*/$HOME/.ssh/$MATCH}(N.)) ;;
        host)
          hosts+=(${(z)value}) ;;
        match)
          [[ $value == (#i)(|*[[:space:]])(|original)host[[:space:]]##(#b)([^[:space:]]##)* ]] \
            && hosts+=(${(s:,:)match[1]}) ;;
      esac
    done
  done
  reply=(${(u)${hosts:#*[*?%!]*}})
}
zstyle -e ':completion:*:hosts' hosts '_dotfiles_hosts'
zstyle ':completion:*' users ${${(f)"$(</etc/passwd)"}%%[#:]*} disaster
zstyle ':completion:*:(ssh|scp|rsync):*:users' ignored-patterns \
        adm amanda apache at avahi avahi-autoipd backup beaglidx bin cacti canna \
        clamav colord daemon dbus debian-spamd distcache dnsmasq dovecot fax ftp games gdm \
        gkrellmd geoclue gnats gopher hacluster haldaemon halt hplip hsqldb ident irc junkbust kdm \
        kernoops ldap list lp mail mailman mailnull man messagebus mldonkey mysql nagios \
        named netdump news nfsnobody nobody nm-openconnect nscd ntp nut nvidia-persistenced nx obsrun openvpn \
        operator pcap polkitd postfix postgres privoxy proxy pulse pvm quagga radvd \
        rpc rpcuser rpm rtkit saned scard shutdown speech-dispatcher squid sshd statd svn sync sys syslog tftp \
        usbmux uucp uuidd vcsa wwwrun whoopsie xfs '_*'

# ... unless we really want to.
zstyle '*' single-ignored show

# Ignore multiple entries.
zstyle ':completion:*:(rm|kill|diff):*' ignore-line other
zstyle ':completion:*:rm:*' file-patterns '*:all-files'

# Kill
zstyle ':completion:*:*:*:*:processes' command 'ps -u $USER -o pid,user,comm -w'
zstyle ':completion:*:*:kill:*:processes' list-colors '=(#b) #([0-9]#) ([0-9a-z-]#)*=01;34=0=01'
zstyle ':completion:*:*:kill:*' menu yes select
zstyle ':completion:*:*:kill:*' force-list always
zstyle ':completion:*:*:kill:*' insert-ids single

# Man
zstyle ':completion:*:manuals' separate-sections true
zstyle ':completion:*:manuals.(^1*)' insert-sections true

# SSH/SCP/RSYNC
zstyle ':completion:*:(scp|rsync):*' tag-order 'hosts:-host:host hosts:-domain:domain hosts:-ipaddr:ip\ address *'
zstyle ':completion:*:(scp|rsync):*' group-order users files all-files hosts-domain hosts-host hosts-ipaddr
zstyle ':completion:*:ssh:*' tag-order 'hosts:-host:host hosts:-domain:domain hosts:-ipaddr:ip\ address *'
zstyle ':completion:*:ssh:*' group-order users hosts-domain hosts-host users hosts-ipaddr
zstyle ':completion:*:(ssh|scp|rsync):*:hosts-host' ignored-patterns '*(.|:)*' loopback ip6-loopback localhost ip6-localhost broadcasthost
zstyle ':completion:*:(ssh|scp|rsync):*:hosts-domain' ignored-patterns '<->.<->.<->.<->' '^[-[:alnum:]]##(.[-[:alnum:]]##)##' '*@*'
zstyle ':completion:*:(ssh|scp|rsync):*:hosts-ipaddr' ignored-patterns '^(<->.<->.<->.<->|(|::)([[:xdigit:].]##:(#c,2))##(|%*))' '127.0.0.<->' '255.255.255.255' '::1' 'fe80::*'

# TELNET
zstyle ':completion:*:telnet:*' tag-order 'hosts:-host:host hosts:-domain:domain hosts:-ipaddr:ip\ address *'
zstyle ':completion:*:telnet:*' group-order hosts-domain hosts-host users hosts-ipaddr
zstyle ':completion:*:telnet:*:hosts-host' ignored-patterns '*(.|:)*' loopback ip6-loopback localhost ip6-localhost broadcasthost
zstyle ':completion:*:telnet:*:hosts-domain' ignored-patterns '<->.<->.<->.<->' '^[-[:alnum:]]##(.[-[:alnum:]]##)##' '*@*'
zstyle ':completion:*:telnet:*:hosts-ipaddr' ignored-patterns '^(<->.<->.<->.<->|(|::)([[:xdigit:].]##:(#c,2))##(|%*))' '127.0.0.<->' '255.255.255.255' '::1' 'fe80::*'

# Ping/Traceroute
compdef ping6=ping
compdef traceroute6=traceroute

# Tools whose packaged zsh completion is unusable: Arch's sops file starts
# with a blank line, so compinit skips its #compdef, and git-lfs ships an empty
# file. Source the script the tool generates instead, cached until the tool
# is updated. A tool is skipped once compinit has a completion for it.
() {
  local dir=$ZSH_CACHE_DIR/generated cmd bin out
  local -A generators=(
    git-lfs 'completion zsh'
    sops    'completion zsh'
  )
  for cmd in ${(k)generators}; do
    bin=${commands[$cmd]}
    [[ -n $bin && -z ${_comps[$cmd]} ]] || continue
    out=$dir/_$cmd
    if [[ ! -s $out || ${bin:A} -nt $out ]]; then
      [[ -d $dir ]] || mkdir -p $dir
      if ! { $bin ${=generators[$cmd]} >| $out.tmp 2>/dev/null && [[ -s $out.tmp ]] }; then
        rm -f $out.tmp
        continue
      fi
      mv -f $out.tmp $out
    fi
    source $out
  done
}

# Commands that only ship a bash completion: complete them through
# bashcompinit. The bash file is sourced on the first TAB. Files that need the
# bash-completion helpers (_init_completion, _filedir, ...), refuse to load
# outside bash (BASH_VERSION) or source other files (BASH_SOURCE) are left
# out. The list of usable files is cached until a package changes the
# completions directory or this file changes.
# bashcompinit does not emulate bash exactly (compgen -W does not expand
# variables, for one), so when the bash function offers nothing the files are
# completed as before.
_dotfiles_bash_completion_dir=${DOTFILES_BASH_COMPLETION_DIR:-/usr/share/bash-completion/completions}
typeset -gA _dotfiles_bash_specs
_dotfiles_bash_completion() {
  local cmd=$service
  if [[ -z ${_dotfiles_bash_specs[$cmd]} ]]; then
    source $_dotfiles_bash_completion_dir/$cmd 2>/dev/null
    # `complete -F func cmd` in the bash file replaced this loader.
    if [[ ${_comps[$cmd]} == _bash_complete\ * ]]; then
      _dotfiles_bash_specs[$cmd]=${_comps[$cmd]}
    else
      _dotfiles_bash_specs[$cmd]=_default
    fi
    _comps[$cmd]=_dotfiles_bash_completion
  fi
  ${=_dotfiles_bash_specs[$cmd]} "$@" 2>/dev/null || _default "$@"
}
() {
  local dir=$_dotfiles_bash_completion_dir list=$ZSH_CACHE_DIR/bash-completions
  local file cmd skip='(_init_completion|_comp_[a-z]|_filedir|_get_comp_words_by_ref|__ltrim_colon|_split_longopt|_known_hosts|_parse_help|_parse_usage|_command_offset|_longopt|_count_args|_have |_usergroup|_pids|_pnames|_services|_modules|_kernel_versions|_available_interfaces|_ip_addresses|_mac_addresses|_xfunc|_tilde|_quote_readline|_expand|_cd |_root_command|_allowed_users|_allowed_groups|_cd_devices|_dvd_devices|_terms|_fstypes|_signals|_uids|_gids|_shells|_realcommand|_upvars|_variables|BASH_VERSION|BASH_SOURCE)'
  [[ -d $dir ]] || return 0
  if [[ ! -s $list || $dir -nt $list || $ZSH/init/completion.zsh -nt $list ]]; then
    local -a usable
    for file in $dir/*(N.); do
      [[ $(<$file) =~ $skip ]] || usable+=(${file:t})
    done
    print -rl -- $usable >| $list
  fi
  autoload -Uz bashcompinit && bashcompinit
  for cmd in ${(f)"$(<$list)"}; do
    [[ -n ${commands[$cmd]} && -z ${_comps[$cmd]} ]] && compdef _dotfiles_bash_completion $cmd
  done
}
