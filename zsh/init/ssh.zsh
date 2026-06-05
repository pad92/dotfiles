# SSH and Proton Pass Configuration

# Starts the Proton Pass SSH agent daemon if it's not already running.
_start_proton_pass_agent() {
  # Check if pass-cli is available
  (( ${+commands[pass-cli]} )) || return 1

  # Ensure the SSH directory exists
  [[ -d "${HOME}/.ssh" ]] || mkdir -p "${HOME}/.ssh"

  # Start the daemon only if it is not already running
  if ! pass-cli ssh-agent daemon status 2>/dev/null | grep -q "Status:   running"; then
    pass-cli ssh-agent daemon start --create-new-identities=Personal --socket-path "${SSH_AUTH_SOCK}" >/dev/null 2>&1
  fi
}

if [[ -z "${SSH_CONNECTION}" ]]; then
  export SSH_AUTH_SOCK="${HOME}/.ssh/proton-pass-agent.sock"
  _start_proton_pass_agent
fi

# Clean up the function namespace
unset -f _start_proton_pass_agent

