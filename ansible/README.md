# Ansible setup

This directory configures the workstations. It installs the selected package
groups, applies the system settings and deploys the home directory files. The
controller pushes everything over SSH, so a managed node needs no clone of
this repository.

Supported distributions: Arch Linux and CachyOS, Debian and Ubuntu, and
Fedora. Some roles only act on Arch Linux; their README says so.

The documentation goes from the general to the specific:

1. This file covers the requirements, the layout, the inventory, the `make`
   targets and the conventions every role follows.
2. [Playbooks](PLAYBOOKS.md) describes the play in `site.yml`: its
   `pre_tasks`, the role order, the tags, the `when` conditions and the OBS
   profile.
3. Each role has a README (see [Roles](#roles)) with its requirements,
   variables and behavior.

## Requirements

On the controller:

- `ansible-core` 2.21 or later.
- The collections pinned in `requirements.yml` (`ansible.posix`,
  `community.general`). `make galaxy` installs them under
  `.ansible/collections`, and `make galaxy-force` reinstalls them.

On each managed node:

- An SSH server that accepts the user's key. No role configures `sshd`.
- Network access to GitHub, to clone the pinned Zsh and Vim plugins.
- `sudo` rights for the user, since most roles run with `become`.

## Layout

| Path                       | Content                                                  |
| :------------------------- | :------------------------------------------------------- |
| `inventory.yml`            | The workstations, by short hostname.                     |
| `group_vars/all/`          | Settings shared by every host; `vault.yml` is encrypted. |
| `host_vars/<hostname>.yml` | Settings of one host.                                    |
| `site.yml`                 | The playbook, see [PLAYBOOKS.md](PLAYBOOKS.md).          |
| `tasks/`                   | Task files shared by the playbooks (`target.yml`).       |
| `roles/`                   | One role per function.                                   |
| `library/`                 | Custom modules (`dotfiles_*`).                           |
| `module_utils/`            | Code shared by the custom modules.                       |
| `filter_plugins/`          | Custom Jinja filters.                                    |
| `requirements.yml`         | Pinned collections.                                      |

`ansible.cfg`, at the repository root, points Ansible at these directories and
at `.ansible/collections`. It also sets `[diff] always = true`, so every run
shows the diff of the files it changes.

## Running

The `make` targets run `ansible-playbook ansible/site.yml --limit "$HOST"` with
the options below:

```sh
make check BECOME_PASS=1
make deploy BECOME_PASS=1
```

| Variable       | Effect                                                                                             |
| :------------- | :------------------------------------------------------------------------------------------------- |
| `HOST`         | Inventory host or pattern passed to `--limit`. Default: `uname -n` up to the first dot.            |
| `PLAYBOOK`     | Playbook of `ansible/` to run. Only `site` exists; `TAGS=obs` runs its OBS profile.                |
| `TAGS`         | Run only these comma-separated tags (`--tags`).                                                    |
| `SKIP_TAGS`    | Skip these comma-separated tags (`--skip-tags`).                                                   |
| `BECOME_PASS`  | Any non-empty value adds `--ask-become-pass`, which asks for the sudo password once.               |
| `ANSIBLE_ARGS` | Any other `ansible-playbook` option, passed last, such as `-e packages_action=reconcile` or `-vv`. |

The main targets:

- `make deploy` applies the playbook. `make install` is an alias.
- `make check` runs it in check mode (`--check`), with diff mode on.
- `make plan` adds `-e packages_action=plan`. The run prints the package plan,
  then the play ends and nothing changes. It refuses `TAGS` and `SKIP_TAGS`,
  because a tag selection could skip that stop and let later roles change the
  host (see [PLAYBOOKS.md](PLAYBOOKS.md#roles)).
- `make tags` and `make tasks` add `--list-tags` and `--list-tasks`. They run
  no task, so they never ask for the sudo password, even with `BECOME_PASS`.
- `make install-obs` forces `TAGS=obs` and clears `SKIP_TAGS`.
- `make help` lists every target.

## Per-host settings

`inventory.yml` lists the workstations by short hostname. Ansible reaches each
one over SSH, including the machine that runs `make deploy`. SSH resolves the
name through `~/.ssh/config` or DNS; set `ansible_host` in the host's
`host_vars` file when it cannot.

```sh
make check HOST=PadsP5560 BECOME_PASS=1
```

Variables come from several places. From lowest to highest precedence, as in
the official precedence rules:

1. Role defaults (`roles/<role>/defaults/main.yml`).
2. `group_vars/all/`, shared by every host.
3. `host_vars/<hostname>.yml`, which overrides `group_vars/all/` for one host.
4. Play `vars` in `site.yml`. They override `host_vars`, so
   `packages_group_selection` and `packages_state_merge_selection` cannot be
   set per host.
5. Role `vars/` and `include_vars` files (`dotfiles`, `gpu`, `packages`), which
   hold internal values a host should not change.
6. Extra vars (`-e` in `ANSIBLE_ARGS`), which override everything for one run.

The shared files:

- `group_vars/all/packages.yml` defines `packages_workstation_groups`, the
  package groups both workstations share.
- `group_vars/all/main.yml` holds the shared desktop settings: the external
  monitors, where they sit and the workspaces they open. Monitors are matched
  by make and model, so they need no Vault.

A host file sets what differs on one machine:

```yaml
# host_vars/PadsP5560.yml
packages_host_groups: "{{ packages_workstation_groups + ['23_vpn'] }}"
hardening_ipv6_enabled: false
dotfiles_hypridle_enabled: false
```

To add a machine, add its short hostname (`uname -n | cut -d. -f1`) to
`inventory.yml` and create `host_vars/<hostname>.yml`, even an empty one.

### Hostname check

The first `pre_tasks` of `site.yml` (in `tasks/target.yml`) compare the
`hostname` fact of the machine reached with `inventory_hostname`, and the play
stops when they differ:

```text
PadsP5560 reached a machine named PadsTower, which its host_vars do not
describe. Fix the SSH address of PadsP5560.
```

The check exists because `host_vars` describe the monitors, sensors and
packages of one machine. A wrong `ansible_host`, a stale DNS record or an SSH
alias pointing elsewhere would otherwise apply them to another computer. The
comparison is case-sensitive and uses the short hostname. To fix it, point
`ansible_host` or `~/.ssh/config` at the right machine, or rename the
inventory entry to match `uname -n | cut -d. -f1` on the managed node.

## Vault

The Vault is optional. When `.vault` (ignored by Git) exists at the repository
root, the `make` targets export it as `ANSIBLE_VAULT_PASSWORD_FILE`. Set
`DOTFILES_VAULT_PASSWORD_FILE=/path` to use another file. A clone without
`.vault` runs without the Vault. Only the `vpn` role reads from it, for its
gateway.

## Role conventions

- One role per function. A role's variables start with its name, for example
  `dns_manage` or `cpu_power_amd_pstate_epp`. `defaults/main.yml` holds the
  default values with comments.
- Each role README follows the `ansible-galaxy role init` template:
  Requirements, Role Variables, Dependencies, Example Playbook, License and
  Author Information. Sections specific to the role sit between Role Variables
  and Dependencies.
- Each role has a `meta/main.yml` with its Galaxy information (description,
  platforms, tags) and no `dependencies`. The play sets the order.
- Roles stay generic. Hardware and hosts are detected from facts or set in
  `host_vars`, never written in a role.
- Tasks call modules by their FQCN, such as `ansible.builtin.template`. When
  no module fits, a custom module of `library/` does the work and reports each
  file it writes (sysfs controls, package builds, initramfs images, backups).
- With `packages_action=plan`, the roles before `packages` are skipped by a
  `when` condition and `packages` ends the play after the plan, so `make plan`
  changes nothing.
- Check mode changes nothing and reports what a run would do.
- A conflicting file, directory or link at a managed path is moved to `.bak`.
  The move is atomic and refuses an existing target, so a run stops before it
  overwrites an earlier backup.

### Custom modules

| Module                     | Purpose                                                       |
| :------------------------- | :------------------------------------------------------------ |
| `dotfiles_aur`             | Install AUR packages with yay or paru.                        |
| `dotfiles_backup`          | Move a conflicting path to `.bak` atomically.                 |
| `dotfiles_initramfs`       | Regenerate the initramfs and report the images written.       |
| `dotfiles_makepkg`         | Build a package with makepkg and report its output.           |
| `dotfiles_obsolete_files`  | Delete former role files that still hold the shipped content. |
| `dotfiles_retired_plugins` | Remove the Vundle and tpm leftovers, keeping unsaved work.    |
| `dotfiles_sysfs`           | Write sysfs controls and report the changes.                  |
| `dotfiles_tree`            | List a source tree, hidden files and links included.          |

## Cleaning up

`make clean` removes what deployments and earlier versions left behind. It
runs `scripts/clean_obsolete.py` with the Python interpreter of
`ansible-playbook`; set `ANSIBLE_PYTHON` to use another one.

In the home directory (`CLEAN_ROOT`, `$HOME` by default) it handles:

- The backups the `dotfiles` role made next to the paths it manages
  (`<path>.bak` and `<path>.<pid>.<date>@<time>~`).
- Broken links under the paths the role deploys, such as a link into a
  deleted `~/.dotfiles` clone or a `.wants` link to a unit that is gone. Other
  broken links in the home are left alone.
- Files a role no longer ships, such as the former `10-realtime.conf` of the
  `audio` role, while they still hold the shipped content. An edited copy or a
  link is kept and reported.

In `/etc`, it lists the Ansible backups (`<path>.<pid>.<date>@<time>~`) of the
files the roles manage, as listed in `SYSTEM_MANAGED_FILES` of
`scripts/ansible_backup_files.py`. They belong to root, so run
`sudo make clean CLEAN_ROOT=$HOME` to remove them. A plain run keeps and
reports them.

In the repository, it removes:

- The Git metadata of the retired submodules (Vundle, tpm, dotbot and the Zsh
  plugins): their `[submodule]` sections and their clones under
  `.git/modules`. This only happens from the main worktree. A clone with a
  commit that no remote branch or tag holds, or whose checkout still exists,
  is kept and reported.
- The records of worktrees whose directory is gone.
- Python tool caches and untracked broken links. Nested Git checkouts and
  Python virtual environments are not searched.

In `~/.local/share/applications` and `~/.config/autostart`, it lists the
`.desktop` launchers that can no longer start, with the reason next to each
one: the `TryExec` or `Exec` program is missing, the `WINEPREFIX` they set is
gone, or the `steam://rungameid/<id>` game has no `appmanifest` in any native
or Flatpak Steam library. The launchers the `dotfiles` role deploys are left
to it. An absence counts only when it is certain, so a path on an unmounted
fstab filesystem or on removable media (`/media`, `/run/media`) keeps its
launcher, and so does a game whose Steam library is missing. Empty folders
left behind (such as `wine/Programs/<game>`) are removed, and
`update-desktop-database` refreshes the MIME cache when there is one. Under
`sudo` the launchers are skipped with a note, since root's `PATH` would hide
the owner's programs. Run `make clean` as the home's owner to check them.

Everything is listed before anything changes. Backups, launchers, submodule
metadata and worktree records are removed only after you type `REMOVE` on a
terminal; without a terminal they stay. Caches, broken links and unchanged
obsolete files go without asking.

| Variable              | Effect                                                            |
| :-------------------- | :---------------------------------------------------------------- |
| `DRY_RUN`             | `1` lists only, `0` or empty removes. Any other value is refused. |
| `CLEAN_ROOT`          | Home directory to clean. Default: `ANSIBLE_BACKUP_ROOT`.          |
| `ANSIBLE_BACKUP_ROOT` | Former name of `CLEAN_ROOT`, still read. Default: `$HOME`.        |
| `ANSIBLE_PYTHON`      | Python interpreter that runs the script.                          |

`make ansible-backup-ls` and `make ansible-backup-rm` remain as aliases of
`make clean DRY_RUN=1` and `make clean`.

## Roles

`site.yml` runs them in this order. [PLAYBOOKS.md](PLAYBOOKS.md#roles) gives
their tags, `when` conditions and `become` setting.

| Role                                                   | Function                                                                                    |
| :----------------------------------------------------- | :------------------------------------------------------------------------------------------ |
| [`package_manager`](roles/package_manager/README.md)   | Configure pacman (`/etc/pacman.conf`, `multilib`) and makepkg.                              |
| [`packages`](roles/packages/README.md)                 | Select package groups, then install and reconcile their packages.                           |
| [`lact`](roles/lact/README.md)                         | Write the LACT GPU profiles for the GPUs that LACT reports.                                 |
| [`gaming`](roles/gaming/README.md)                     | Check the Steam group's services and make power-profiles-daemon the only CPU power manager. |
| [`package_services`](roles/package_services/README.md) | Enable the services of the selected package groups.                                         |
| [`docker`](roles/docker/README.md)                     | Add `docker_group_users` to the `docker` group.                                             |
| [`hardening`](roles/hardening/README.md)               | Apply the desktop sysctl policy and the SSH client defaults.                                |
| [`dns`](roles/dns/README.md)                           | Make systemd-resolved the only resolver, for the host and Docker.                           |
| [`vpn`](roles/vpn/README.md)                           | Configure the openfortivpn SAML VPN from the Ansible Vault.                                 |
| [`gpu`](roles/gpu/README.md)                           | Configure the NVIDIA and i915 kernel modules and hybrid runtime PM.                         |
| [`cpu_power`](roles/cpu_power/README.md)               | Apply the AMD EPP and X3D settings and read which power manager runs.                       |
| [`time_sync`](roles/time_sync/README.md)               | Enable systemd-timesyncd when no other NTP client is enabled or running.                    |
| [`power_save`](roles/power_save/README.md)             | Write audio (and opt-in Wi-Fi) power-saving module options on a portable machine.           |
| [`iwlwifi`](roles/iwlwifi/README.md)                   | Write the Intel Wi-Fi module options a host lists in `/etc/modprobe.d/iwlwifi.conf`.        |
| [`wireless_regdom`](roles/wireless_regdom/README.md)   | Set the Wi-Fi regulatory domain in `/etc/conf.d/wireless-regdom`.                           |
| [`gnome_keyring`](roles/gnome_keyring/README.md)       | Add the `pam_gnome_keyring.so` rules to `/etc/pam.d/login`.                                 |
| [`dotfiles`](roles/dotfiles/README.md)                 | Deploy the home directory files and the user units.                                         |
| [`audio`](roles/audio/README.md)                       | Write the PipeWire and WirePlumber user configuration: clean microphone and voice effects.  |
| [`agent_cli`](roles/agent_cli/README.md)               | Set the Claude Code and Codex status lines and Claude Code token savings.                   |
| [`obs`](roles/obs/README.md)                           | Configure OBS Studio and its virtual camera for `22_obs`.                                   |
| [`print3d`](roles/print3d/README.md)                   | Configure F3D thumbnails of 3D files for Nautilus, for `24_3dprint` (tag `3dprint`).        |
