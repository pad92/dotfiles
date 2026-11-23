# dotfiles

Deploys the user configuration of a Hyprland workstation into the SSH user's
home directory. Static files come from `files/home/`, which mirrors the home
layout, and the files that depend on host settings are rendered from
`templates/home/`. Everything is copied from the controller's clone of the
repository, so the target needs no clone and keeps no link into one.

## Requirements

- Runs as the SSH user, without privilege escalation (`become: false`). The
  play gathers that user's facts, which set `dotfiles_home`, `dotfiles_owner`
  and `dotfiles_group`.
- A running user systemd manager, for the user units and the handlers.
- Network access to GitHub on the target, to clone the pinned Zsh and Vim
  plugins when they are missing or their pin changes.

## Role Variables

Hosts usually set the Hyprland, hypridle and Waybar variables, in
`group_vars/all/main.yml` or `host_vars/<hostname>.yml` (see
[Per-host settings](../../README.md#per-host-settings)). The other variables
describe what the role ships and rarely need a change. `defaults/main.yml`
comments each one.

| Variable                               | Default                                                                              | Description                                                                                              |
| :------------------------------------- | :----------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------- |
| `dotfiles_home`                        | `ansible_facts['user_dir']`                                                          | Home directory of the SSH user.                                                                          |
| `dotfiles_owner`                       | `ansible_facts['user_id']`                                                           | Owner of the deployed files.                                                                             |
| `dotfiles_group`                       | `ansible_facts['user_gid']`, as a string                                             | Group of the deployed files.                                                                             |
| `dotfiles_source_repository`           | Three levels above `role_path`                                                       | Controller clone, the source of the Git-tracked file lists.                                              |
| `dotfiles_source_root`                 | `{{ role_path }}/files/home`                                                         | Source of the static files.                                                                              |
| `dotfiles_legacy_link_root`            | `~/.dotfiles/ansible/roles/dotfiles/files/home`                                      | Where earlier versions linked the trees. Follows `dotfiles_link_root` or `dotfiles_repository` when set. |
| `dotfiles_icon_theme`                  | `Papirus-Dark`                                                                       | Icon theme of the GTK 2 and 3, hyprtoolkit and Mako configurations.                                      |
| `dotfiles_icon_theme_parent`           | `dotfiles_icon_theme` without a `-Dark` suffix                                       | Parent theme that Mako also searches. Set it to the theme's `Inherits=` value otherwise.                 |
| `dotfiles_zsh_dest`                    | `.local/share/dotfiles/zsh`                                                          | Zsh tree, relative to the home directory.                                                                |
| `dotfiles_zsh_home`                    | `{{ dotfiles_home }}/{{ dotfiles_zsh_dest }}`                                        | Absolute path of the Zsh tree.                                                                           |
| `dotfiles_trees`                       | `.vim` and `zsh`                                                                     | Trees copied with only their Git-tracked files.                                                          |
| `dotfiles_manifest_directory`          | `{{ dotfiles_home }}/.local/state/dotfiles/manifests`                                | Manifests of the copied directories.                                                                     |
| `dotfiles_zsh_plugins`                 | Three `zsh-users` plugins                                                            | Zsh plugins cloned at a pinned commit.                                                                   |
| `dotfiles_vim_pack_plugins`            | gruvbox, vim-gitgutter, vim-fugitive, colorizer, editorconfig-vim                    | Vim plugins cloned at a pinned commit into `~/.vim/pack/dotfiles/start/`.                                |
| `dotfiles_retired_plugin_paths`        | `.vim/bundle`, `.tmux/plugins`                                                       | Vundle and tpm leftovers to remove.                                                                      |
| `dotfiles_retired_plugin_parents`      | `.tmux`                                                                              | Parents removed once empty.                                                                              |
| `dotfiles_hyprlock_wallpaper_source`   | An Arch wallpaper under `assets/wallpapers/`                                         | Hyprlock background in the repository.                                                                   |
| `dotfiles_hyprlock_wallpaper`          | `.local/share/dotfiles/wallpapers/<file name>`                                       | Where the background is copied.                                                                          |
| `dotfiles_directories`                 | 15 directories, `.bin` and `.config/*`                                               | Directories copied file by file.                                                                         |
| `dotfiles_directory_handlers`          | See [Handlers](#handlers)                                                            | Handlers notified by a change in a copied directory.                                                     |
| `dotfiles_file_handlers`               | See [Handlers](#handlers)                                                            | Handlers notified by a change to one file.                                                               |
| `dotfiles_systemd_directory`           | `.config/systemd`                                                                    | Source and destination of the user units.                                                                |
| `dotfiles_openrazer_group`             | `25_razer`                                                                           | Package group that enables the OpenRazer daemon. Keep it equal to `packages_razer_group`.                |
| `dotfiles_openrazer_enabled`           | `true` when `25_razer` is in `packages_selected_groups`                              | Enable `openrazer-daemon.service`.                                                                       |
| `dotfiles_openrazer_unit`              | `/usr/lib/systemd/user/openrazer-daemon.service`                                     | Unit that must exist before it is enabled.                                                               |
| `dotfiles_hypridle_enabled`            | `true`                                                                               | `false` stops and disables `hypridle.service`.                                                           |
| `dotfiles_obsolete_user_unit_links`    | Two Tracker 3 links and the `arch-update.timer` link                                 | Unit links removed while they are broken.                                                                |
| `dotfiles_systemd_graphical_units`     | 8 units                                                                              | User units enabled and started with the graphical session.                                               |
| `dotfiles_files`                       | 15 files                                                                             | Single files copied to the home directory.                                                               |
| `dotfiles_templates`                   | 10 templates                                                                         | Templates and their destinations. An entry may set its own `mode`.                                       |
| `dotfiles_template_mode`               | `'0644'`                                                                             | Mode of rendered files.                                                                                  |
| `dotfiles_portable_form_factors`       | Convertible, Detachable, Hand Held, Laptop, Notebook, Portable, Sub Notebook, Tablet | DMI chassis types that count as portable.                                                                |
| `dotfiles_is_portable`                 | `true` when `form_factor` is in the list above                                       | Override when the firmware reports the wrong chassis type.                                               |
| `dotfiles_hypridle_lock_timeout`       | `300`                                                                                | Seconds before the session locks.                                                                        |
| `dotfiles_hypridle_dpms_timeout`       | `900`                                                                                | Seconds before the screens turn off.                                                                     |
| `dotfiles_hypridle_suspend_timeout`    | `0`                                                                                  | Seconds before suspend. `0` adds no suspend listener.                                                    |
| `dotfiles_hypr_monitors`               | `[]`                                                                                 | Monitors and where they sit. See [Monitors](#monitors).                                                  |
| `dotfiles_hypr_monitor_mode`           | `preferred`                                                                          | `preferred`, `highrr` or `highres`.                                                                      |
| `dotfiles_hypr_workspace_rules`        | `[]`                                                                                 | Hyprland workspace rules: `workspace`, `monitor` (a layout name), `default`.                             |
| `dotfiles_hypr_window_rules`           | `[]`                                                                                 | Hyprland window rules: `match`, `monitor` (a layout name).                                               |
| `dotfiles_hypr_effects_enabled`        | `not dotfiles_is_portable`                                                           | Blur and shadows.                                                                                        |
| `dotfiles_hypr_touch_monitor`          | `''`                                                                                 | Layout name of the monitor that receives touch input. Empty leaves it unset.                             |
| `dotfiles_waybar_modules_right`        | See `defaults/main.yml`                                                              | Right-hand Waybar modules.                                                                               |
| `dotfiles_waybar_portable_modules`     | `backlight`, `battery`                                                               | Modules added on a portable machine.                                                                     |
| `dotfiles_waybar_temperature_sensors`  | `[]`                                                                                 | Sensors of the `temperature#<name>` modules.                                                             |
| `dotfiles_waybar_temperature_critical` | `90`                                                                                 | Default critical temperature of a sensor.                                                                |
| `dotfiles_waybar_includes`             | Five files under `~/.config/waybar/conf/`                                            | Module definitions included by the Waybar configuration.                                                 |

External variables:

- `packages_selected_groups`, from the `packages` role, read for the OpenRazer
  group with an empty default.
- `dotfiles_link_root` and `dotfiles_repository`, set only by inventories of
  earlier versions.

`vars/main.yml` derives the values that the templates read, such as the active
Waybar modules and the Hyprland effects. Do not override them.

## Deployment

`files/home/` keeps the home-relative layout: `files/home/.config/hypr/`
deploys to `~/.config/hypr/`. Scripts under `files/home/.bin/` deploy to
`~/.bin/`, which Zsh adds to `PATH`. To add a file that needs variables, put
its template under `templates/home/` and add it to `dotfiles_templates`.

The role validates its settings before it changes anything
(`tasks/validate.yml`) and stops with a message that names the expected
format.

Directories are checked and copied one file at a time. The read-only
`dotfiles_tree` module lists their content, including hidden files, empty
directories and source symlinks, and detects link cycles. Each changed path
shows in the task output and notifies the directory's handlers. A file is
backed up before its content is replaced. Existing directory permissions and
files you added stay untouched.

Before deploying, the `dotfiles_backup` module moves each conflicting regular
file, directory, or symlink that points elsewhere to `<path>.bak`. The move is
atomic and keeps ownership, permissions, hard links and extended attributes. A
backed-up symlink keeps its target, and the target is left alone. When a
`.bak` path already exists, the deployment stops before replacing anything. To
restore a backup, move the deployed path aside, then move the `.bak` path back.
In check mode, conflicts show as planned backups, and the tasks that would
replace them wait until the paths have really moved.

Rendered files belong to `dotfiles_owner` and `dotfiles_group`, with
`dotfiles_template_mode` unless their `dotfiles_templates` entry sets a `mode`.

### Manifests

Each copied directory has a manifest in `dotfiles_manifest_directory` that
lists the files deployed there with their SHA-1. The next deployment deletes
the files of the old manifest that the repository no longer ships, as long as
they are still regular files with the same checksum. A file you changed or
replaced with a link is kept and reported. A file you added is never listed,
so it stays. A first deployment has no manifest and deletes nothing. Check
mode reports the deletions without making them. When a directory leaves
`dotfiles_directories` or `dotfiles_trees`, its manifest is deleted and its
files are left in place.

## Vim and Zsh trees

`dotfiles_trees` copies `.vim` to `~/.vim` and `zsh` to `dotfiles_zsh_dest`.
Only the files Git tracks in the controller's clone are copied, so its Vim
backups and installed plugins stay on the controller. Files that programs add
to a tree on the target, such as plugins, backups and swap files, stay in
place. `dotfiles_tree` refuses a submodule in a copied tree, because its files
would not be copied.

The repository has no submodules and no plugin manager. The plugins of
`dotfiles_zsh_plugins` and `dotfiles_vim_pack_plugins` are cloned on the target
at their pinned commits. The Vim plugins form a Vim package that Vim loads at
startup (`:help packages`). To update a plugin, change its `version` to the new
commit and deploy. The clone moves to that commit, and the files removed
upstream go with it. A clone with local changes stops the deployment. The
`package_vim` jobs read the same list, through
`scripts/ci/fetch_vim_plugins.py`, to build `vim.tar.gz`.

### Retired plugin managers

Vundle and tpm are gone, along with tmux-sensible, whose settings are now in
`.tmux.conf`. A deployment removes what they left in the home directory
(`dotfiles_retired_plugin_paths`):

- It first checks every Git repository under those paths. If one has
  uncommitted or untracked changes, a stash, or commits that no remote branch
  holds, the deployment stops, names it, and removes nothing.
- A path that holds anything besides Git repositories, such as a
  `.netrwhist` file or a plugin copied by hand, moves whole to `<path>.bak`.
  So does a path that is a plain file. Empty directories do not count. An
  existing `.bak` stops the deployment before any change.
- `~/.tmux` is removed once empty. If it still holds something, such as
  tmux-resurrect sessions, it is kept and the run reports it. A `~/.tmux` link
  into `~/.dotfiles` loses only the link, and its target is not followed.

Check mode lists what would be removed and what would move to `.bak`. Files
that Vundle and tpm wrote through a link stay in the clone, under
`files/home/.vim/bundle/` and `files/home/.tmux/plugins/`. The role never
deletes inside the clone, so remove them by hand or delete the clone.

### Links from earlier versions

Earlier versions linked the trees into `~/.dotfiles`. When a tree is still a
link into `dotfiles_legacy_link_root`, the deployment:

1. Copies to `<path>.migrating` what the link holds beyond the shipped files:
   untracked files such as Vim backups and swap files, and tracked files edited
   through the link. It leaves out `.vim/bundle/`, which would be removed
   anyway, and the pinned plugins, which are cloned instead. The Zsh plugins
   that older versions shipped as submodules have a `.git` file pointing into
   the clone.
2. Removes the link and renames `<path>.migrating` into place.
3. Copies the tree. A file edited through the link is replaced by the shipped
   one and kept as a timestamped backup.

A run stopped after removing the link leaves `<path>.migrating`, which the next
run renames. The clone is left untouched. A link whose clone was already
deleted is replaced with nothing to bring over. Check mode lists the files it
would bring over and stops before the replacement. A link that points anywhere
else is backed up to `<path>.bak` like any other conflict.

Up to the same versions, `~/.config/waybar/config` was a link to a
`config.<hostname>` file. The deployment removes that link, leaves its target
alone, and renders the file in its place. Copies of the removed per-host files
(`config.<hostname>`, `temperature.<hostname>.json`, `hosts/<hostname>.lua`,
`is-host.sh`) stay in the home directory and are no longer read.

## Host-dependent files

The role ships one template per file, never a copy per hostname. Templates
read variables only, and Ansible makes the host decisions:

| File                                     | Variables                                                                                                            |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `~/.config/waybar/config`                | `dotfiles_waybar_modules_right`, `dotfiles_waybar_portable_modules`, `dotfiles_waybar_includes`                      |
| `~/.config/waybar/conf/temperature.json` | `dotfiles_waybar_temperature_sensors`                                                                                |
| `~/.config/hypr/hypridle.conf`           | `dotfiles_hypridle_lock_timeout`, `_dpms_timeout`, `_suspend_timeout`                                                |
| `~/.config/hypr/hosts/settings.lua`      | `dotfiles_hypr_monitors`, `_monitor_mode`, `_workspace_rules`, `_window_rules`, `_touch_monitor`, `_effects_enabled` |

`dotfiles_is_portable` is true when the `form_factor` fact, read from the DMI
chassis type, is in `dotfiles_portable_form_factors`. Set it in
`host_vars/<hostname>.yml` when the firmware reports the wrong type. On a
portable machine, Waybar adds the backlight and battery modules and Hyprland
turns off blur and shadows.

`hypridle.conf` gets a suspend listener only when
`dotfiles_hypridle_suspend_timeout` is above 0. PadsTower sets 3600.

### Monitors

Hyprland's `include/host.lua` applies `hosts/settings.lua` and does not look at
the hostname. No resolution, refresh rate, scale or position is written
anywhere. Hyprland picks the mode from `dotfiles_hypr_monitor_mode`:

- `preferred`: the mode the monitor's EDID prefers.
- `highrr`: the highest refresh rate.
- `highres`: the highest resolution.

Hyprland derives the scale from the panel's density. An entry's own `mode`
overrides the policy for that monitor. For example, under `highrr`, a 60 Hz
monitor that also offers 75 Hz at a lower resolution would switch to that
lower resolution, so give it `mode: preferred`. An entry with `bitdepth: 10`
gets a 10-bit framebuffer, which HDR games and films need. Hyprland's default
is 8 bits.

`include/layout.lua` positions the monitors from the size each one reports, at
startup and whenever a monitor is plugged in or unplugged. Each entry of
`dotfiles_hypr_monitors` names one display and says where it sits:

```yaml
dotfiles_hypr_monitors:
  - name: dell
    match: Dell Inc. DELL P2423DE # start of the description, no serial
    mode: preferred # optional, overrides dotfiles_hypr_monitor_mode
  - name: asus
    match: ASUSTek COMPUTER INC XG32WCS
    right_of: dell
    bitdepth: 10 # optional, 8 or 10
  - name: laptop
    internal: true # the built-in eDP, LVDS or DSI panel
    below: dell
```

`match` is the start of the `description:` line of `hyprctl monitors all`,
which Hyprland's `desc:` selector also matches. A monitor placed with
`right_of`, `left_of`, `above` or `below` shares an edge with its neighbor, so
the cursor can cross. A monitor that would overlap another slides along its
neighbor's edge to the nearest free place, and moves further in the same
direction only when there is none. The first monitor without a relation sits
at 0,0. The layout stays connected whatever is plugged in: a monitor whose
neighbor is not connected, or that no entry matches, joins the right edge of
the rightmost monitor. With an empty list, every monitor is lined up that way,
in connector order.

Names must be unique. Several identical monitors need one entry each, all with
the same `match`. They pair with the monitors in connector-name order, so a
given cabling always gives the same layout. To pin an entry to one physical
monitor, add its serial number to `match` (`Dell Inc. DELL P2423DE 0000000`).
The longest match chooses first. Keep a serial number in the Vault if it must
stay out of Git. Workspace rules, window rules and
`dotfiles_hypr_touch_monitor` refer to these names. A rule on one of several
identical monitors, or on the built-in panel, follows the connector the
monitor is plugged into.

### Waybar

Waybar is in English only, including the clock (`en_US.UTF-8`). Its tooltips
share one layout: `Name: state` on the first line, then details, then one line
per click (`click: action`, then `right-click: action`). A tooltip shows no
click line when the click would do nothing or fail. Custom modules escape what
they print, since Waybar reads their tooltip as Pango markup.
`tests/test_waybar_tooltips.py` checks the layout, that each format string uses
known placeholders, and that no French label remains.

A `temperature#<name>` module appears only when
`dotfiles_waybar_temperature_sensors` has a sensor of that name. Each sensor
takes `name`, `label`, `hwmon_path`, `input_filename` and an optional
`critical_threshold`:

```yaml
dotfiles_waybar_temperature_sensors:
  - name: cpu
    label: CPU
    hwmon_path: /sys/devices/platform/coretemp.0/hwmon
    input_filename: temp1_input
```

Use the device path that contains the `hwmonN` directory, because the number
changes between boots.

The `custom/lact-profile` module refreshes every 30 seconds. Its tooltip shows
the active LACT profile, the state of power-profiles-daemon with its profile,
and the state of ananicy-cpp. A click cycles the LACT profiles `Auto`,
`Adaptive` and `PreferMaximumPerformance`, which the
[lact](../lact/README.md) role creates. When one of them is missing, the module
shows `GPU profiles?`, lists them, and drops the click hint. The module is
hidden when LACT does not answer.

## Handlers

`dotfiles_directory_handlers` maps copied directories to handlers:

| Directory                    | Handler                               |
| :--------------------------- | :------------------------------------ |
| `.config/hypr`               | Restart Hyprlauncher, if it runs.     |
| `.config/uwsm`               | Print a reminder to log in again.     |
| `.config/waybar`             | Reload Waybar.                        |
| `.config/xdg-desktop-portal` | `try-restart` the XDG desktop portal. |

UWSM reads its environment files at session start, hence the reminder.
Hyprlauncher is relaunched as a UWSM service, so Ansible does not wait for the
launcher to exit.

`dotfiles_file_handlers` maps single files to handlers, for programs that do
not watch their configuration:

| File                                   | Handler                                                      |
| :------------------------------------- | :----------------------------------------------------------- |
| `.config/hypr/hypridle.conf`           | `try-restart hypridle.service`.                              |
| `.config/hypr/hosts/settings.lua`      | Reload Hyprland, if it runs.                                 |
| `.config/hypr/hyprtoolkit.conf`        | Restart Hyprlauncher, which reads the theme only at startup. |
| `.config/mako/config`                  | Reload Mako, if it runs.                                     |
| `.config/waybar/config`                | Reload Waybar.                                               |
| `.config/waybar/conf/temperature.json` | Reload Waybar.                                               |

A file handler also runs when a deployment deletes its file from a copied
tree. `try-restart` leaves a stopped or disabled service alone. The PipeWire
and WirePlumber files belong to the `audio` role.

## User systemd units

The role copies the user units from `files/home/.config/systemd/`, reloads the
user systemd manager after a change, and runs `try-restart` on the changed
units, which leaves inactive services stopped. It then enables and starts
`dotfiles_systemd_graphical_units`. These service jobs are queued without
waiting for them to finish, so a successful play confirms the submission only.
If a service does not start, check `systemctl --user --failed` and
`journalctl --user -b`.

Hypridle is enabled by default. To stop it on one machine, set this in its
`host_vars/<hostname>.yml`:

```yaml
dotfiles_hypridle_enabled: false
```

`false` stops the service and disables its automatic start. With `true`,
`hypridle.service` starts with the other graphical units, so it must stay in
`dotfiles_systemd_graphical_units`.

`openrazer-daemon.service` is not shipped as a link. When the `25_razer` group
is selected and `dotfiles_openrazer_unit` exists, the role enables it with
`systemctl --user enable`. It never disables it, since an unplugged device does
not prove the host has none.

`dotfiles_obsolete_user_unit_links` lists unit links the repository no longer
ships, relative to `~/.config/systemd/user`. The role deletes each one that is
still a broken symlink. It leaves alone a regular file at that path, and a
link to an installed unit, which `systemctl --user enable` created on the
host.

### AppImage integration

`appimage-integrate.path` watches `~/Applications` and starts
`appimage-integrate.service`, which also runs once at login. For each
`*.AppImage`, `~/.bin/appimage-integrate.py` reads the embedded desktop entry
and icon with 7-Zip, without running the AppImage, and writes
`~/.local/share/applications/appimage-<id>.desktop` and
`~/.local/share/icons/appimage/<id>.<ext>`. The ID comes from the embedded
desktop file, so a new version replaces the old entry. The script removes only
the entries it wrote (`X-AppImage-Integrate-Source`) once their AppImage is
gone, and it skips an AppImage that another desktop entry already launches.
Run it by hand with `systemctl --user start appimage-integrate.service`.

## GPU selection

At session start, `~/.config/uwsm/gpu-devices.sh` lists the DRM cards and puts
the unique boot VGA card first, then the other GPUs. The firmware's boot choice
does not say whether a card is integrated or dedicated. With several GPUs and
no unique boot VGA card, or no usable card, the script leaves the selection
unchanged and prints why, so Aquamarine uses its default or an existing
override. The device list uses the current DRM nodes, without card numbers or
PCI addresses. The selection happens at login, so log in again after changing
the GPU hardware.

Applications still choose their own driver, Vulkan and VA-API included. Use
`prime-run <application>` for workloads that need the NVIDIA GPU, after
removing any session-wide `VK_DRIVER_FILES` override. Keep LACT on `Auto` for
office use.

## Claude Code status line

`~/.bin/claude-statusline` renders the Claude Code status line on one line, in
the colors of `pad.zsh-theme`: model, reasoning effort, directory, Git state,
open merge request, context gauge, subscription limits and changed lines. The
`agent_cli` role adds it to the Claude Code settings, and it needs `jq`.

The gauge is followed by the tokens in the context window and the window size,
rounded down: `ctx ▰▰▰▱▱▱▱▱▱▱ 31% 63k/200k`. Compact when it turns yellow (50%)
or red (80%). The count is hidden until the first response. Each limit shows
its usage and the time left before it resets, rounded down: `16% 2h` for the
5-hour window, then `3% 4j` for the 7-day window, in hours during its last
day. Segments without data are hidden. The estimated cost appears only when no
subscription limit is reported, because it is a list-price estimate.
`NO_COLOR` disables colors.

## Tags

| Tag                 | Runs                                                                       |
| :------------------ | :------------------------------------------------------------------------- |
| `dotfiles`          | The whole role. In `site.yml`, also the `audio` and `agent_cli` roles.     |
| `dotfiles_deploy`   | Validation and deployment, including the plugin clones and the user units. |
| `systemd`           | The user units and the graphical units.                                    |
| `hyprlock_carousel` | The Hyprlock carousel helper.                                              |

See [Running](../../README.md#running) for how to pass tags.

## Dependencies

None. In `site.yml` it runs after the system roles, as the SSH user.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: dotfiles
      become: false
      tags: [dotfiles]
```

## License

Unlicense

## Author Information

pad
