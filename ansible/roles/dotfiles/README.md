# Dotfile role

`files/home/` mirrors paths under a user's home directory. The role copies
static configuration and user scripts, renders templates, and links the
Git-backed Vim, tmux, and Zsh trees. `templates/home/` contains files that use
Ansible variables.

Keep static files in their home-relative layout. For example,
`files/home/.config/hypr/` deploys to `~/.config/hypr/`. Add variable-aware
files under `templates/home/` and register them in `defaults/main.yml`. Scripts
under `files/home/.bin/` deploy to `~/.bin/`, which Zsh adds to `PATH`.

For local deployments, `dotfiles_deploy` compares all static directories in one
read-only `rsync` pass, checking file contents and permissions. Only directories
with changes reach Ansible's recursive copy step. That step still creates
timestamped backups and notifies the directory's reload handlers. Extra local
files remain untouched. Templates, individual dotfiles and systemd units keep
their usual Ansible checks.

The comparison also runs with `--check`, without writing files. If `rsync` is
missing or the comparison fails, the role reports the fallback and checks every
directory with Ansible. Remote connections use the regular copy path. No
additional collection is required; `rsync` is already in the base package list.

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
must be running. Hyprlauncher is relaunched as a UWSM service so Ansible does
not wait for the launcher to exit. Changed unit definitions use `try-restart`;
audio configuration uses `try-reload-or-restart`. Both leave inactive services
stopped. Service jobs, including the initial graphical service starts, are
queued without waiting for completion. A successful play therefore confirms
submission, not service health; inspect `systemctl --user --failed` and
`journalctl --user -b` if a service does not start.

Set `dotfiles_update_vim_plugins=true` to check for Vim and update its plugins.
By default, the role skips both commands.

Both Waybar layouts include the LACT indicator. Its tooltip shows the active
LACT profile, the power-profiles-daemon profile and service state, and the
ananicy-cpp service state. Missing services and read errors are reported there.
The tooltip refreshes every five seconds; clicking still cycles LACT profiles.
The indicator is hidden when LACT is unavailable. The script uses Python's
standard library and `powerprofilesctl`, supplied by power-profiles-daemon.
Deploy with `dotfiles_deploy`; the role reloads Waybar when its configuration
changes.
