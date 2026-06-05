if [ -z "${SSH_CONNECTION}" ]; then
  _runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
  _ssh_agent_sockets=(
    "${HOME}/.ssh/proton-pass-agent.sock"
    "${HOME}/.1password/agent.sock"
    "${_runtime_dir}/ssh-agent.socket"
    "${_runtime_dir}/keyring/ssh"
    "${_runtime_dir}/gcr/ssh"
    "${_runtime_dir}/gnupg/S.gpg-agent.ssh"
  )

  for agent_sock in "${_ssh_agent_sockets[@]}"; do
    if [ -S "${agent_sock}" ]; then
      export SSH_AUTH_SOCK="${agent_sock}"
      break
    fi
  done
  unset _ssh_agent_sockets _runtime_dir
fi

