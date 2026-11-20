# Playbooks

`site.yml` is the only playbook. It applies the [roles](README.md#roles) to
the workstations of the inventory, from packages to system settings to the
home directory. `make deploy` runs all of it, and `make deploy TAGS=obs` runs
the [OBS profile](#obs-profile). The [Ansible guide](README.md) covers the
inventory, the per-host settings and the `make` targets. Each role's README
documents its variables.

## Pre-tasks

These steps are tagged `always` and run before any role, whatever tags you
pass:

1. `tasks/target.yml` gathers the facts as the SSH user, not as root, so
   `user_id`, `user_dir` and `env` describe the account whose home the roles
   configure. It then stops if the machine reports another hostname than its
   inventory name, because its `host_vars` describe other monitors and
   packages.
2. A check of the distribution.
3. The package groups are selected (`include_role` of `packages`,
   `tasks_from: selection`). This step reads the host without changing it and
   sets `packages_selected_groups` for the roles that need it.

## Roles

`site.yml` supports Arch Linux and CachyOS, Debian and Ubuntu, and Fedora.
The play runs with `become`, except the home roles, which set
`become: false`.

| Order | Role               | Tags                         | Runs when                                           |
| ----: | :----------------- | :--------------------------- | :-------------------------------------------------- |
|     1 | `package_manager`  | `package_manager`            | not `plan`                                          |
|     2 | `packages`         | `packages`, `obs`            | always                                              |
|     3 | `lact`             | `system`, `lact`             | not `plan`                                          |
|     4 | `gaming`           | `system`, `gaming`           | not `plan`, Arch Linux, `21_steam` selected         |
|     5 | `package_services` | `system`, `package_services` | not `plan`                                          |
|     6 | `docker`           | `system`, `docker`           | not `plan`, `12_containers_docker` selected         |
|     7 | `hardening`        | `system`, `hardening`        | not `plan`                                          |
|     8 | `dns`              | `system`, `dns`              | not `plan`                                          |
|     9 | `vpn`              | `system`, `vpn`              | not `plan`, `23_vpn` selected                       |
|    10 | `gpu`              | `system`, `gpu`              | not `plan`                                          |
|    11 | `cpu_power`        | `system`, `cpu_power`        | not `plan`                                          |
|    12 | `time_sync`        | `system`, `time_sync`        | not `plan`                                          |
|    13 | `power_save`       | `system`, `power_save`       | not `plan`                                          |
|    14 | `iwlwifi`          | `system`, `iwlwifi`          | not `plan`                                          |
|    15 | `wireless_regdom`  | `system`, `wireless_regdom`  | not `plan`, Arch Linux                              |
|    16 | `gnome_keyring`    | `system`, `gnome_keyring`    | not `plan`, Arch Linux, `gnome_keyring_pam_enabled` |
|    17 | `dotfiles`         | `dotfiles`                   | always                                              |
|    18 | `audio`            | `dotfiles`, `audio`          | not `plan`                                          |
|    19 | `agent_cli`        | `dotfiles`, `agent_cli`      | always                                              |
|    20 | `obs`              | `obs`                        | `22_obs` selected                                   |
|    21 | `print3d`          | `3dprint`                    | not `plan`, Arch Linux, `24_3dprint` selected       |

"not `plan`" means `packages_action` is not `plan`. `make plan` sets it, so
the run prints the package plan and changes nothing.

Each role has one tag named after it. Two group tags cover several roles:
`system` runs the host roles from `lact` to `gnome_keyring` plus the makepkg
tasks of `package_manager`, and `dotfiles` runs the three home roles. A few
roles also have finer tags for part of their tasks, listed in their README.
`make tags` prints every tag.

The [main README](../README.md#ansible-tags) lists the tags with what each
one does.

### Handlers

Changed files notify their handlers: Mako and Waybar reload, the audio
services reload or restart (the SwayOSD server restarts with them), and active
user units whose definitions changed restart after `daemon-reload`. Service
jobs are queued without waiting, so a successful play confirms submission,
not service health: check `systemctl --user --failed` afterwards.

### Examples

```sh
make deploy BECOME_PASS=1
make check TAGS=dotfiles
make deploy TAGS=packages,gaming BECOME_PASS=1
make deploy BECOME_PASS=1 ANSIBLE_ARGS="-e packages_action=reconcile"
```

## OBS profile

When `obs` is the only tag, `site.yml` installs OBS and nothing else. The
`packages` role installs `22_obs` and the GPU groups that `lspci` detects,
then the `obs` role configures OBS. The other roles are skipped by the tag
selection. With other tags next to it, `obs` only selects the `obs` role and
the host's usual package selection applies.

- The profile needs Arch Linux or CachyOS, the only distributions that
  define the OBS packages.
- `packages_state_merge_selection: true` adds these groups to the selection
  saved on the workstation instead of replacing it.
- The profile refuses `packages_action=reconcile`, since every other managed
  package would look obsolete. The check runs before the facts are gathered.
  To reconcile, run without tags.
- When a `*-dkms` package is selected, the headers of the running kernel are
  installed too. Their name comes from the package that owns
  `/usr/lib/modules/<kernel>/vmlinuz`, for example `linux-zen-headers`.

```sh
make deploy TAGS=obs BECOME_PASS=1
```

`make install-obs` runs the same command.
