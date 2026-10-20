# Dotfile role

`files/home/` mirrors paths under a user's home directory. The role copies
static configuration and user scripts, renders templates, and links the
Git-backed Vim, tmux, and Zsh trees. `templates/home/` contains files that use
Ansible variables.

Keep static files in their home-relative layout. For example,
`files/home/.config/hypr/` deploys to `~/.config/hypr/`. Add variable-aware
files under `templates/home/` and register them in `defaults/main.yml`. Scripts
under `files/home/.bin/` deploy to `~/.bin/`, which Zsh adds to `PATH`.

Before deployment, the role moves conflicting regular files and directories to
`<path>.bak`. If a required backup path already exists, deployment stops before
moving the conflict or removing any conflicting managed symlinks. Symlinks at
managed paths are replaced when they point elsewhere. To restore a backup, move
the deployed path aside, then move the `.bak` path back.

`dotfiles_directory_handlers` maps copied directories to reload handlers. The
defaults restart Hyprlauncher or reload Mako and Waybar when their configuration
directories change. Selecting a different host-specific Waybar configuration
also reloads Waybar. The role reloads the user systemd manager after unit
changes and before starting the configured services. A user systemd manager
must be running.

Set `dotfiles_update_vim_plugins=true` to check for Vim and update its plugins.
By default, the role skips both commands.
