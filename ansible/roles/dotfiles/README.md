# Dotfile role

`files/home/` mirrors paths under a user's home directory. The role copies
static configuration and user scripts, renders templates, and links the
Git-backed Vim, tmux, and Zsh trees. `templates/home/` contains files that use
Ansible variables.

Keep static files in their home-relative layout. For example,
`files/home/.config/hypr/` deploys to `~/.config/hypr/`. Add variable-aware
files under `templates/home/` and register them in `defaults/main.yml`. Scripts
under `files/home/.bin/` deploy to `~/.bin/`, which Zsh adds to `PATH`.

The role checks and copies directory contents one file at a time with Ansible.
The read-only `dotfiles_tree` module includes hidden files, empty directories,
and source symlinks while detecting cycles. File writes use `copy` and `file`.
Each changed path appears in the task output and notifies the directory's
reload handlers. Existing file contents are backed up before replacement.
Existing directory permissions and extra local files remain untouched. Templates,
individual dotfiles and systemd units use their own Ansible tasks as well.

Before deployment, the role backs up conflicting regular files and directories
to `<path>.bak` with the `dotfiles_backup` module. Its atomic move preserves
ownership, permissions, hard links and extended attributes. If a required backup path already exists, deployment
stops before replacing the conflict. Managed symlinks are handled separately;
their targets remain untouched. To restore a backup, move the deployed path
aside, then move the `.bak` path back. In check mode, existing conflicts are
reported as planned backups; replacement tasks are deferred until the paths
have actually been moved.

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

Hypridle is enabled by default. Configure individual machines in
`ansible/host_vars/localhost.yml` using the detected hostname:

```yaml
dotfiles_hypridle_enabled_by_hostname:
  PadsP5560: true
  PadsTower: false
```

A `false` value stops the user service and disables its automatic startup.
A `true` value keeps the normal graphical-unit activation; `hypridle.service`
must remain in `dotfiles_systemd_graphical_units`. Hosts absent from the map
use `dotfiles_hypridle_enabled_default`, which defaults to `true`.
A running user systemd manager is required to apply either state.

Set `dotfiles_update_vim_plugins=true` to update the declared Vim plugin
checkouts with `ansible.builtin.git`. Each checkout path appears in Ansible's
output. By default, plugin updates are skipped.

Both Waybar layouts include the LACT indicator. Its tooltip shows the active
LACT profile, the power-profiles-daemon profile and service state, and the
ananicy-cpp service state. Missing services and read errors are reported there.
The tooltip refreshes every five seconds; clicking still cycles LACT profiles.
The indicator is hidden when LACT is unavailable. The script uses Python's
standard library and `powerprofilesctl`, supplied by power-profiles-daemon.
Deploy with `dotfiles_deploy`; the role reloads Waybar when its configuration
changes.
