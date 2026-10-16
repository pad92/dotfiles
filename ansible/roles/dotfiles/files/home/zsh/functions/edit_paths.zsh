# The following functions append/prepend a directory to a named path variable.
# Existing occurrences are removed before the new position is applied.
# Examples:
#
# Prepend `~/bin` to `$PATH`:
#   prepend_path PATH ~/bin
#
# Append `~bin` to `$PATH` instead:
#  append_path PATH ~/bin
# (this will remove `~/bin` from the beginning of `$PATH` first)
#
# Append `~/lib/python-2.7/site-packages` to `$PYTHONPATH`:
#  append_path PYTHONPATH ~/lib/python-2.7/site-packages
#
# and so on ...


_is_path_variable_name() {
  [[ "$1" =~ '^[A-Za-z_][A-Za-z0-9_]*$' ]]
}

remove_from_path() {
  if (( $# != 2 )); then
    print -u2 -- 'Usage: remove_from_path VARIABLE DIRECTORY'
    return 2
  fi

  local name="$1"
  local directory="$2"
  local current result='' entry
  local -a entries

  if ! _is_path_variable_name "$name"; then
    print -u2 -- "Invalid path variable name: $name"
    return 2
  fi

  current="${(P)name}"
  entries=("${(@s/:/)current}")
  for entry in "${entries[@]}"; do
    [[ "$entry" == "$directory" ]] && continue
    if [[ -n "$result" ]]; then
      result+=":$entry"
    else
      result="$entry"
    fi
  done

  export "$name=$result"
}

# Add path to start of named path, removing any occurrences
# already in it, e.g.
#   prepend_path PATH ~/bin
#   prepend_path PYTHONPATH ~/my-py-stuff
prepend_path() {
  if (( $# != 2 )); then
    print -u2 -- 'Usage: prepend_path VARIABLE DIRECTORY'
    return 2
  fi

  local name="$1"
  local directory="$2"
  local current

  [[ -d "$directory" ]] || return 0
  _is_path_variable_name "$name" || return 2
  remove_from_path "$name" "$directory" || return
  current="${(P)name}"
  export "$name=$directory${current:+:$current}"
}

# As above, but add to end of path
append_path() {
  if (( $# != 2 )); then
    print -u2 -- 'Usage: append_path VARIABLE DIRECTORY'
    return 2
  fi

  local name="$1"
  local directory="$2"
  local current

  [[ -d "$directory" ]] || return 0
  _is_path_variable_name "$name" || return 2
  remove_from_path "$name" "$directory" || return
  current="${(P)name}"
  export "$name=${current:+$current:}$directory"
}
