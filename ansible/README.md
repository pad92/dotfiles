# Ansible setup

This directory configures the workstations: it installs the selected package
groups, applies the system settings, and deploys the home directory files.
Everything is copied from the controller over SSH, so a target needs no clone
of this repository.

Supported distributions: Arch Linux and CachyOS, Debian and Ubuntu, and
Fedora. Some roles only act on Arch Linux; their README says so.

Documentation goes from the general to the specific:

1. This file: requirements, layout, inventory, `make` targets and the rules
   every role follows.
2. [Playbooks](PLAYBOOKS.md): what `site.yml` and `obs.yml` run, in which
   order, with which tags and conditions.
3. The README of each role (see [Roles](#roles)): its requirements,
   variables and behavior.

## Requirements

On the controller:

- `ansible-core` 2.21 or later.
- The collections pinned in `requirements.yml` (`ansible.posix`,
  `community.general`). `make galaxy` installs the missing ones under
  `.ansible/collections`.

On each target:

- An SSH server that accepts the user's key. No role configures `sshd`.
- Network access to GitHub, to clone the pinned Zsh and Vim plugins.
- `sudo` for the user, for the roles that change the system.

## Layout

| Path                       | Content                                                  |
| :------------------------- | :------------------------------------------------------- |
| `inventory.yml`            | The workstations, by hostname.                           |
| `group_vars/all/`          | Settings shared by every host; `vault.yml` is encrypted. |
| `host_vars/<hostname>.yml` | Settings of one host.                                    |
| `site.yml`, `obs.yml`      | Playbooks, described in [PLAYBOOKS.md](PLAYBOOKS.md).    |
| `tasks/`                   | Tasks shared by the playbooks (`target.yml`).            |
| `roles/`                   | One role per function.                                   |
| `library/`                 | Custom modules (`dotfiles_*`).                           |
| `module_utils/`            | Code shared by the custom modules.                       |
| `filter_plugins/`          | Custom Jinja filters.                                    |
| `requirements.yml`         | Pinned collections.                                      |

`ansible.cfg`, at the repository root, points Ansible at these directories.

## Running

The `make` targets run `ansible-playbook` on `HOST`, this machine by default:

```sh
make check BECOME_PASS=1
make deploy BECOME_PASS=1
```

| Variable       | Effect                                                                |
| :------------- | :-------------------------------------------------------------------- |
| `HOST`         | Inventory host to configure. Default: `uname -n` up to the first dot. |
| `PLAYBOOK`     | `site` (default) or `obs`.                                            |
| `TAGS`         | Run only these tags.                                                  |
| `SKIP_TAGS`    | Skip these tags.                                                      |
| `BECOME_PASS`  | `1` asks for the sudo password.                                       |
| `ANSIBLE_ARGS` | Any other `ansible-playbook` option, such as `-e var=value`.          |

`make check` previews a run with `--check` and diffs. `make plan` prints the
package plan and changes nothing. `make tags` and `make tasks` list what a run
would do. `make help` lists every target.

## Per-host settings

`inventory.yml` lists the workstations by short hostname, and Ansible reaches
each one over SSH, the machine that runs `make deploy` included. SSH resolves
the name through `~/.ssh/config` or DNS; set `ansible_host` in the host file
when it cannot.

```sh
make check HOST=PadsP5560 BECOME_PASS=1
```

Ansible loads `host_vars/<hostname>.yml` on top of `group_vars/all/`. The
playbooks stop if the machine reports another hostname than its inventory
name, because its `host_vars` describe other monitors and packages.

- `group_vars/all/packages.yml` defines `packages_workstation_groups`, the
  package groups both workstations share.
- `group_vars/all/main.yml` holds the shared desktop settings: the external
  monitors, where they sit, and the workspaces they open. Monitors are
  identified by make and model, so they need no Vault.
- A host file sets what differs:

```yaml
# host_vars/PadsP5560.yml
packages_host_groups: "{{ packages_workstation_groups + ['23_vpn'] }}"
hardening_ipv6_enabled: false
dotfiles_hypridle_enabled: false
```

To add a machine, add its short hostname (`hostname -s`) to `inventory.yml`
and create `host_vars/<hostname>.yml`, even an empty one. A `-e` option still
overrides any setting for one run.

## Vault

The Vault is optional. When `.vault` (ignored by Git) exists at the repository
root, the `make` targets export it as `ANSIBLE_VAULT_PASSWORD_FILE`. Set
`DOTFILES_VAULT_PASSWORD_FILE=/path` to use another file. A clone without
`.vault` runs without the Vault. The `vpn` role reads its gateway from it.

## Role conventions

- One role per function. A role's variables start with its name, for example
  `dns_manage` or `cpu_power_amd_pstate_epp`. Each role documents them in its
  README, and `defaults/main.yml` holds the values with comments.
- Each role has a `meta/main.yml` with its Galaxy information (description,
  platforms, tags) and no dependency: the playbooks set the order.
- Roles stay generic: hardware and hosts are detected from facts or set in
  `host_vars`, never written in a role.
- Changes go through Ansible modules. When no module fits, a custom module of
  `library/` does the work and reports each file it writes (sysfs controls,
  package builds, initramfs images, backups).
- Roles that change the host skip `packages_action=plan`, so `make plan`
  changes nothing.
- Check mode changes nothing and reports what a run would do.
- A conflicting file, directory or link at a managed path is moved to `.bak`
  with an atomic move that refuses an existing target, so a run stops before
  overwriting an earlier backup.

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

`make clean DRY_RUN=1` lists the backups created for the managed dotfiles,
and `make clean` removes them after you type `REMOVE`, together with the other
leftovers described in the [main README](../README.md). It runs with the Python
interpreter of `ansible-playbook`; set `ANSIBLE_PYTHON` to use another. The
home is `$HOME` by default; set `CLEAN_ROOT=/path` to select another one.

## Roles

`site.yml` runs them in this order; [PLAYBOOKS.md](PLAYBOOKS.md) gives the tags
and conditions.

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
| [`power_save`](roles/power_save/README.md)             | Write Wi-Fi and audio power-saving module options on a portable machine.                    |
| [`wireless_regdom`](roles/wireless_regdom/README.md)   | Set the Wi-Fi regulatory domain in `/etc/conf.d/wireless-regdom`.                           |
| [`gnome_keyring`](roles/gnome_keyring/README.md)       | Add the `pam_gnome_keyring.so` rules to `/etc/pam.d/login`.                                 |
| [`dotfiles`](roles/dotfiles/README.md)                 | Deploy the home directory files and the user units.                                         |
| [`audio`](roles/audio/README.md)                       | Write the PipeWire and WirePlumber user configuration: clean microphone and voice effects.  |
| [`agent_cli`](roles/agent_cli/README.md)               | Set the Claude Code and Codex status lines.                                                 |
| [`obs`](roles/obs/README.md)                           | Configure OBS Studio and its virtual camera for `22_obs`.                                   |
| [`print3d`](roles/print3d/README.md)                   | Configure F3D thumbnails of 3D files for Nautilus, for `24_3dprint` (tag `3dprint`).        |
