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

Before deployment, the role backs up conflicting regular files, directories and
symlinks that point elsewhere to `<path>.bak` with the `dotfiles_backup` module. Its atomic move preserves
ownership, permissions, hard links and extended attributes. If a required backup path already exists, deployment
stops before replacing the conflict. A backed-up symlink keeps its target, which
remains untouched. To restore a backup, move the deployed path
aside, then move the `.bak` path back. In check mode, existing conflicts are
reported as planned backups; replacement tasks are deferred until the paths
have actually been moved.

## Host-dependent files

The role ships one template per file, never a copy per hostname. Templates
read variables only; the host decisions are made in Ansible:

| File                                     | Variables                                                                                          |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `~/.config/waybar/config`                | `dotfiles_waybar_modules_right`, `dotfiles_waybar_portable_modules`, `dotfiles_waybar_includes`    |
| `~/.config/waybar/conf/temperature.json` | `dotfiles_waybar_temperature_sensors`                                                              |
| `~/.config/hypr/hypridle.conf`           | `dotfiles_hypridle_lock_timeout`, `_dpms_timeout`, `_suspend_timeout`                              |
| `~/.config/hypr/hosts/settings.lua`      | `dotfiles_hypr_monitors`, `_workspace_rules`, `_window_rules`, `_touch_output`, `_effects_enabled` |

`dotfiles_is_portable` is true when the `form_factor` fact, read from the DMI
chassis type, names a laptop or another portable chassis. Set it in
`group_vars/host_<hostname>.yml` when the firmware reports the wrong type. On
a portable machine Waybar adds the backlight and battery modules, and
Hyprland turns off blur and shadows (`dotfiles_hypr_effects_enabled`).

A Waybar `temperature#<name>` module appears only when
`dotfiles_waybar_temperature_sensors` has a sensor of that name:

```yaml
dotfiles_waybar_temperature_sensors:
  - name: cpu
    label: CPU
    hwmon_path: /sys/devices/platform/coretemp.0/hwmon
    input_filename: temp1_input
```

Use the device path that contains the `hwmonN` directory: the number changes
between boots.

Hyprland's `include/host.lua` applies `hosts/settings.lua` and no longer looks
at the hostname. A monitor is a `hl.monitor()` table; quote `mode` and
`position`, because YAML reads `0x1440` as a hexadecimal number. A monitor
whose `output` is empty is left out, together with the workspace and window
rules that target it, and the generic rule of `conf/monitors.lua` handles the
display. That is what happens to the shared Dell and ASUS monitors when
`vault_dotfiles_monitor_outputs` is not defined (see `ansible/README.md`).

`hypridle.conf` gets a suspend listener only when
`dotfiles_hypridle_suspend_timeout` is above 0; PadsTower sets 3600.

The role checks these settings before it changes anything (`tasks/validate.yml`)
and stops with a message naming the expected format. Rendered files belong to
the user who runs the playbook (`dotfiles_owner`, `dotfiles_group`) and use
`dotfiles_template_mode` (`0644`) unless the `dotfiles_templates` entry sets a
`mode`.

Up to this version, `~/.config/waybar/config` was a link to a
`config.<hostname>` file. Deployment removes that link, leaves its target
alone, and renders the file in its place. Copies of the removed per-host files
(`config.<hostname>`, `temperature.<hostname>.json`, `hosts/<hostname>.lua`,
`is-host.sh`) stay in the home directory and are no longer read.

## Handlers

`dotfiles_directory_handlers` maps copied directories to reload handlers. The
defaults restart Hyprlauncher, the XDG desktop portal, or reload Mako and Waybar
when their configuration directories change. A change under `.config/uwsm`
prints a reminder to log in again, because UWSM reads it at session start.
`dotfiles_file_handlers` maps single files to handlers when the program does not
watch its configuration: a changed `.config/hypr/hypridle.conf` runs
`try-restart hypridle.service`, which leaves a stopped or disabled service alone. A changed Waybar
configuration or temperature file reloads Waybar, and a changed
`hosts/settings.lua` reloads a running Hyprland. The role reloads the user systemd manager after unit
changes and before starting the configured services. A user systemd manager
must be running. Hyprlauncher is relaunched as a UWSM service so Ansible does
not wait for the launcher to exit. Changed unit definitions use `try-restart`;
audio configuration uses `try-reload-or-restart`. Both leave inactive services
stopped. Service jobs, including the initial graphical service starts, are
queued without waiting for completion. A successful play therefore confirms
submission, not service health; inspect `systemctl --user --failed` and
`journalctl --user -b` if a service does not start.

`dotfiles_obsolete_user_unit_links` lists unit links the repository no longer
ships, relative to `~/.config/systemd/user`. Deployment deletes each one that is
still a symlink and leaves a regular file at that path alone.

Hypridle is enabled by default. To stop it on one machine, set this in its
`ansible/group_vars/host_<hostname>.yml`:

```yaml
dotfiles_hypridle_enabled: false
```

A `false` value stops the user service and disables its automatic startup.
A `true` value keeps the normal graphical-unit activation; `hypridle.service`
must remain in `dotfiles_systemd_graphical_units`. Hosts without the setting
use the role default, `true`.
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

## Claude Code status line

`~/.bin/claude-statusline` renders the Claude Code status line on one line with
the colors of `pad.zsh-theme`: model, reasoning effort, directory, Git state,
open merge request, context gauge, subscription limits and changed lines. The
gauge is followed by the tokens in the context window and its size, rounded
down: `ctx ▰▰▰▱▱▱▱▱▱▱ 31% 63k/200k`. Compact when it turns yellow (50 %) or
red (80 %); the count is hidden until the first response. Each
limit shows its usage and the time left before it resets, rounded down: `16% 2h`
for the 5-hour window, then `3% 4j` for the 7-day window (in hours during its
last day). Segments without data are hidden. The
estimated cost appears only when no subscription limit is reported, because it
is a list-price estimate. `NO_COLOR` disables colors. The script needs `jq`.

The `agent_cli` role adds this script to the Claude Code settings.
