#
# Sets terminal window and tab titles.
#
# Authors:
#   James Cox <james@imaj.es>
#   Sorin Ionescu <sorin.ionescu@gmail.com>
#

# Dumb terminals lack support.
if [[ "$TERM" == 'dumb' ]]; then
  return
fi

# Set the GNU Screen window number.
if [[ -n "$WINDOW" ]]; then
  export SCREEN_NO="%B${WINDOW}%b "
else
  export SCREEN_NO=""
fi

# Sets the GNU Screen title.
function set-screen-title() {
  if [[ "$TERM" == screen* ]]; then
    printf "\ek%s\e\\" ${(V)argv}
  fi
}

# Sets the terminal window title.
function set-window-title() {
  if [[ "$TERM" == ((x|a|ml|dt|E)term*|(u|)rxvt*) ]]; then
    printf "\e]2;%s\a" ${(V)argv}
  fi
}

# Sets the terminal tab title.
function set-tab-title() {
  if [[ "$TERM" == ((x|a|ml|dt|E)term*|(u|)rxvt*) ]]; then
    printf "\e]1;%s\a" ${(V)argv}
  fi
}

# Sets the tab and window titles with the command name.
function set-title-by-command() {
  emulate -L zsh
  setopt LOCAL_OPTIONS EXTENDED_GLOB

  # Get the command name that is under job control.
  if [[ "${1[(w)1]}" == (fg|%*)(\;|) ]]; then
    # Get the job name, and, if missing, set it to the default %+.
    local job_name="${${1[(wr)%*(\;|)]}:-%+}"

    # Make a local copy for use in the subshell.
    local -A jobtexts_from_parent_shell
    jobtexts_from_parent_shell=(${(kv)jobtexts})

    jobs $job_name 2>/dev/null > >(
      read index discarded
      # The index is already surrounded by brackets: [1].
      set-title-by-command "${(e):-\$jobtexts_from_parent_shell$index}"
    )
  else
    # Set the command name, or in the case of sudo or ssh, the next command.
    local cmd=${1[(wr)^(*=*|sudo|ssh|-*)]}

    # Right-truncate the command name to 15 characters.
    if (( $#cmd > 15 )); then
      cmd="${cmd[1,15]}..."
    fi


    for kind in window tab screen; do
      set-${kind}-title "${USER}@${HOST}: $cmd"
    done
  fi
}

# Don't override precmd/preexec; append to hook array.
autoload -Uz add-zsh-hook

# Sets the tab and window titles before the prompt is displayed.
function set-title-precmd() {
  set-window-title "${USER}@${HOST}: ${(%):-%~}"
  for kind in tab screen; do
    # Left-truncate the current working directory to 15 characters.
    set-${kind}-title "${USER}@${HOST}: ${(%):-%15<...<%~%<<}"
  done
}
add-zsh-hook precmd set-title-precmd

# Sets the tab and window titles before command execution.
function set-title-preexec() {
  set-title-by-command "$2"
}
add-zsh-hook preexec set-title-preexec
