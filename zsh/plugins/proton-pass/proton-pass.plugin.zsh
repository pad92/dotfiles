# Do nothing if pass-cli is not installed
(( ${+commands[pass-cli]} )) || return

# Handy aliases for Proton Pass CLI
alias proton-pass="pass-cli"
alias proton-pass-item="pass-cli item"
alias proton-pass-vault="pass-cli vault"
alias proton-pass-totp="pass-cli totp"
alias proton-pass-run="pass-cli run"
alias proton-pass-agent="pass-cli ssh-agent"
alias proton-pass-agent-start="pass-cli ssh-agent daemon start"
alias proton-pass-agent-status="pass-cli ssh-agent daemon status"
alias proton-pass-agent-stop="pass-cli ssh-agent daemon stop"
