# Dotfile role

`files/home/` mirrors paths under a user's home directory. The role copies
static configuration and user scripts, renders templates, and links the
Git-backed Vim, tmux, and Zsh trees. `templates/home/` contains files that use
Ansible variables.

Keep static files in their home-relative layout. For example,
`files/home/.config/hypr/` deploys to `~/.config/hypr/`. Add variable-aware
files under `templates/home/` and register them in `defaults/main.yml`. Scripts
under `files/home/.bin/` deploy to `~/.bin/`, which Zsh adds to `PATH`.
