# Dotfile role

`files/home/` mirrors paths under a user's home directory. The role copies
static configuration, user scripts and the Vim and Zsh trees, and renders
templates. `templates/home/` contains files that use Ansible
variables.

The playbook reaches the target over SSH. Every file comes from the
controller's copy of the repository: nothing in the home directory points
into a clone, so the target needs none, and a clone there can be deleted
once deployed. `dotfiles_home`, `dotfiles_owner` and `dotfiles_group` come
from the facts of the SSH user.

## Vim and Zsh trees

`dotfiles_trees` lists `.vim` and `zsh`, which deploys to
`~/.local/share/dotfiles/zsh` (`dotfiles_zsh_dest`). Only the files Git
tracks are copied. The controller's own Vim backups or installed plugins are
never copied. Files that programs add to a tree on the target (plugins,
backups, swap files) stay in place.

The repository has no submodules and no plugin manager. The Zsh plugins
(`dotfiles_zsh_plugins`) and the Vim plugins (`dotfiles_vim_pack_plugins`)
are cloned on the target at the commit pinned for each one. The Vim plugins
go to `~/.vim/pack/dotfiles/start/`, a Vim package that Vim loads at startup
(`:help packages`). To update a plugin, change its `version` to the new
commit and deploy: the clone moves to that commit, and the files removed
upstream go with it. A clone with local changes stops the deployment. The
`package_vim` jobs read the same list to build `vim.tar.gz`.

vim-instant-markdown does not start its preview on its own:
`plugins.vim` sets `g:instant_markdown_autostart` to 0, since the plugin
reports an error on every Markdown buffer when the `instant-markdown-d`
server is not installed. Run `:InstantMarkdownPreview` to start it.

The packages role installs that server on Arch: `nodejs-instant-markdown-d`
from the AUR, in the `01_base` group. `dotfiles_vim_preview_packages` maps
`ansible_facts['os_family']` to the package that provides it. On a listed
family, the deployment reads `package_facts` and stops before copying
anything if the package is missing; check mode only warns, since the
packages role installs nothing then. Debian and Fedora package no such
server and npm is not used, so those families are not listed and the
preview is unavailable there.

Vundle and tpm are gone, along with tmux-sensible, whose settings are now in
`.tmux.conf`. A deployment removes what they left in the home
(`dotfiles_retired_plugin_paths`): `~/.vim/bundle/` and `~/.tmux/plugins/`.
Before anything else, it checks every Git repository under them. If one has
uncommitted or untracked changes, a stash, or commits that no remote branch
holds, the deployment stops, names it, and removes nothing. `~/.tmux` goes
too once it is empty. If it still holds something, such as tmux-resurrect
sessions, it is kept and the run reports it. A `~/.tmux` link into
`~/.dotfiles`, left by an older version, loses only the link: its target is
not followed or changed. Check mode lists what would be removed.

What Vundle and tpm wrote through a link stays in the clone, under
`files/home/.vim/bundle/` and `files/home/.tmux/plugins/`. The role never
deletes inside the clone, so remove those by hand, or delete the clone.

`dotfiles_tree` refuses a submodule in a copied tree, since its files would
not be copied.

Each copied directory has a manifest in `~/.local/state/dotfiles/manifests/`
(`dotfiles_manifest_directory`) that lists the files deployed there with their
SHA-1. The next deployment deletes the files of the old manifest that the
repository no longer ships, as long as they are still regular files with the
same checksum. A file you changed is kept and reported, and a file you added
is never listed, so it stays. The first deployment with this version has no
manifest yet, so it deletes nothing. Check mode reports the deletions without
making them.

Earlier versions linked these trees into `~/.dotfiles`. When a tree is still a
link there (`dotfiles_legacy_link_root`), the deployment removes the link,
copies the tree, then copies what Git does not track behind the link: Vim
backups and swap files. It leaves out `.vim/bundle/`, which it would only
remove again, and the pinned plugins, which are cloned rather than copied:
the Zsh plugins, which older versions shipped as submodules, have a `.git`
file that points into the clone. The clone itself is left untouched. Check
mode lists the files it will bring over and stops before the replacement. A
link that points anywhere else is backed up to `<path>.bak` like any other
conflict.

The Hyprlock background is copied to
`~/.local/share/dotfiles/wallpapers/` (`dotfiles_hyprlock_wallpaper`).

Keep static files in their home-relative layout. For example,
`files/home/.config/hypr/` deploys to `~/.config/hypr/`. Add variable-aware
files under `templates/home/` and register them in `defaults/main.yml`. Scripts
under `files/home/.bin/` deploy to `~/.bin/`, which Zsh adds to `PATH`.

The role checks and copies directory contents one file at a time with Ansible.
The read-only `dotfiles_tree` module includes hidden files, empty directories,
and source symlinks while detecting cycles. File writes use `copy` and `file`.
Each changed path appears in the task output and notifies the directory's
reload handlers. Existing file contents are backed up before replacement.
Existing directory permissions and extra local files remain untouched; only
files that an earlier deployment copied and the repository dropped are
deleted (see the manifests above). Templates,
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

| File                                     | Variables                                                                                                            |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `~/.config/waybar/config`                | `dotfiles_waybar_modules_right`, `dotfiles_waybar_portable_modules`, `dotfiles_waybar_includes`                      |
| `~/.config/waybar/conf/temperature.json` | `dotfiles_waybar_temperature_sensors`                                                                                |
| `~/.config/hypr/hypridle.conf`           | `dotfiles_hypridle_lock_timeout`, `_dpms_timeout`, `_suspend_timeout`                                                |
| `~/.config/hypr/hosts/settings.lua`      | `dotfiles_hypr_monitors`, `_monitor_mode`, `_workspace_rules`, `_window_rules`, `_touch_monitor`, `_effects_enabled` |

`dotfiles_is_portable` is true when the `form_factor` fact, read from the DMI
chassis type, names a laptop or another portable chassis. Set it in
`host_vars/<hostname>.yml` when the firmware reports the wrong type. On
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
at the hostname. No resolution, refresh rate, scale or position is written
anywhere. Hyprland picks the mode (`dotfiles_hypr_monitor_mode`: `preferred`,
`highrr` or `highres`) and derives the scale from the panel's density.
`include/layout.lua` then positions the monitors from the size each one
reports, at start-up and again whenever a monitor is plugged in or
unplugged. Each entry of `dotfiles_hypr_monitors` names one display and says
where it sits:

```yaml
dotfiles_hypr_monitors:
  - name: dell
    match: Dell Inc. DELL P2423DE # start of the description, no serial
  - name: asus
    match: ASUSTek COMPUTER INC XG32WCS
    right_of: dell
  - name: laptop
    internal: true # the built-in eDP, LVDS or DSI panel
    below: dell
```

`match` is the start of the `description:` line of `hyprctl monitors all`,
which is also what Hyprland's `desc:` selector matches. A neighbour placed
with `right_of`, `left_of`, `above` or `below` shares an edge with it, so
the cursor can cross. A monitor that would overlap another one slides
along its neighbour's edge to the nearest free place; only when there is
none does it move further in the same direction, next to the monitor in
the way. The first monitor without a relation sits at 0,0.
The relations only describe where you want the displays: the layout stays
connected whatever is plugged in. A monitor whose neighbour is not
connected, or that no entry matches, joins the right edge of the rightmost
monitor. With an empty list, every monitor is lined up that way, in
connector order.

Names must be unique. Several identical monitors need one entry each, all
with the same `match`. They pair with the monitors in connector-name order,
so a given cabling always gives the same layout. To pin an entry to one
physical monitor, add its serial number to `match`
(`Dell Inc. DELL P2423DE 0000000`). The longest match chooses first. Keep a
serial number in the Vault if it must stay out of Git. Workspace and window
rules and `dotfiles_hypr_touch_monitor` refer to these names. A rule on one
of several identical monitors, or on the built-in panel, follows the
connector the monitor is plugged into.

`hypridle.conf` gets a suspend listener only when
`dotfiles_hypridle_suspend_timeout` is above 0; PadsTower sets 3600.

The role checks these settings before it changes anything (`tasks/validate.yml`)
and stops with a message naming the expected format. Rendered files belong to
the SSH user (`dotfiles_owner`, `dotfiles_group`) and use
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
`ansible/host_vars/<hostname>.yml`:

```yaml
dotfiles_hypridle_enabled: false
```

A `false` value stops the user service and disables its automatic startup.
A `true` value keeps the normal graphical-unit activation; `hypridle.service`
must remain in `dotfiles_systemd_graphical_units`. Hosts without the setting
use the role default, `true`.
A running user systemd manager is required to apply either state.

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
