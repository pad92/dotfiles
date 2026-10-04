# The system zprofile has already loaded /etc/profile and /etc/profile.d here.
# Start the desktop only from a login shell attached to a terminal.
if [[ -o login && -t 0 ]] && command -v uwsm >/dev/null 2>&1; then
  if uwsm check may-start && uwsm select; then
    exec uwsm start default
  fi
fi
