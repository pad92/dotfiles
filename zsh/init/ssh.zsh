# SSH and Proton Pass Configuration

if [ -z "${SSH_CONNECTION}" ]; then
  export SSH_AUTH_SOCK="${HOME}/.ssh/proton-pass-agent.sock"

  # WSL with Proton Pass Forwarding
  if [ $(command -v npiperelay.exe) ] && [ ! -z ${WSL_DISTRO_NAME+x} ]; then
    # Ensure the .ssh directory exists
    [ -d "${HOME}/.ssh" ] || mkdir -p "${HOME}/.ssh"

    # Configure ssh forwarding to Windows OpenSSH Agent
    # need `ps -ww` to get non-truncated command for matching
    # use square brackets to generate a regex match for the process we want but that doesn't match the grep command running it!
    ALREADY_RUNNING=$(ps -auxww | grep -q "[n]piperelay.exe -ei -s //./pipe/openssh-ssh-agent"; echo $?)
    if [[ $ALREADY_RUNNING != "0" ]]; then
        if [[ -S $SSH_AUTH_SOCK ]]; then
            # not expecting the socket to exist as the forwarding command isn't running (http://www.tldp.org/LDP/abs/html/fto.html)
            echo "removing previous socket..."
            rm $SSH_AUTH_SOCK
        fi
        echo "Starting SSH-Agent relay..."
        # setsid to force new session to keep running
        # set socat to listen on $SSH_AUTH_SOCK and forward to npiperelay which then forwards to openssh-ssh-agent on windows
        (setsid socat UNIX-LISTEN:$SSH_AUTH_SOCK,fork EXEC:"npiperelay.exe -ei -s //./pipe/openssh-ssh-agent",nofork &) >/dev/null 2>&1
    fi
  else
    # Native Linux configuration
    if (( ${+commands[pass-cli]} )); then
      [ -d "${HOME}/.ssh" ] || mkdir -p "${HOME}/.ssh"

      if [ ! -S "${SSH_AUTH_SOCK}" ]; then
        pass-cli ssh-agent daemon start --socket-path "${SSH_AUTH_SOCK}" >/dev/null 2>&1
      fi
    fi
  fi
fi
