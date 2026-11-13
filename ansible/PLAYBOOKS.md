# Playbooks

The playbooks of `ansible/` apply the [roles](README.md#roles) to the
workstations of the inventory. `make deploy` runs `site.yml`;
`PLAYBOOK=obs` selects `obs.yml`. The [Ansible guide](README.md) covers the
inventory, the per-host settings and the `make` targets; each role's README
covers its variables.

| Playbook   | Purpose                                                  |
| :--------- | :------------------------------------------------------- |
| `site.yml` | Configure the whole workstation: packages, system, home. |
| `obs.yml`  | Install and configure OBS Studio only.                   |

## Common pre-tasks

Both playbooks start with the same steps, tagged `always`, so they run
whatever tags are passed:

1. `tasks/target.yml` gathers the facts as the SSH user, not as root, so
   `user_id`, `user_dir` and `env` describe the account whose home the roles
   configure. It then stops if the machine reports another hostname than its
   inventory name, because its `host_vars` describe other monitors and
   packages.
2. A check of the distribution.
3. The package group selection (`include_role` of `packages`,
   `tasks_from: selection`). It only reads the host, and sets
   `packages_selected_groups` for the roles that read it.

## site.yml

Supports Arch Linux and CachyOS, Debian and Ubuntu, and Fedora. The play
escalates with `become`; the home roles run with `become: false`.

| Order | Role               | Tags                                         | Runs when                                           |
| ----: | :----------------- | :------------------------------------------- | :-------------------------------------------------- |
|     1 | `package_manager`  | `package_manager`                            | not `plan`                                          |
|     2 | `packages`         | `packages`                                   | always                                              |
|     3 | `lact`             | `system`, `lact`                             | not `plan`                                          |
|     4 | `gaming`           | `system`, `gaming`                           | not `plan`, Arch Linux, `21_steam` selected         |
|     5 | `package_services` | `system`, `package_services`                 | not `plan`                                          |
|     6 | `docker`           | `system`, `docker`, `package_services`       | not `plan`, `12_containers_docker` selected         |
|     7 | `hardening`        | `system`, `hardening`                        | not `plan`                                          |
|     8 | `dns`              | `system`, `dns`                              | not `plan`                                          |
|     9 | `vpn`              | `system`, `vpn`                              | not `plan`, `23_vpn` selected                       |
|    10 | `gpu`              | `system`, `gpu`, `gpu_modules`               | not `plan`                                          |
|    11 | `cpu_power`        | `system`, `cpu_power`, `amd_cpu_performance` | not `plan`                                          |
|    12 | `time_sync`        | `system`, `time_sync`                        | not `plan`                                          |
|    13 | `power_save`       | `system`, `power_save`                       | not `plan`                                          |
|    14 | `wireless_regdom`  | `system`, `wireless_regdom`                  | not `plan`, Arch Linux                              |
|    15 | `gnome_keyring`    | `system`, `gnome_keyring`                    | not `plan`, Arch Linux, `gnome_keyring_pam_enabled` |
|    16 | `dotfiles`         | `dotfiles`                                   | always                                              |
|    17 | `audio`            | `dotfiles`, `audio`                          | not `plan`                                          |
|    18 | `agent_cli`        | `dotfiles`, `agent_cli`                      | always                                              |
|    19 | `obs`              | `obs`                                        | `22_obs` selected                                   |
|    20 | `print3d`          | `3dprint`                                    | not `plan`, Arch Linux, `24_3dprint` selected       |

"not `plan`" means `packages_action` is not `plan`. `make plan` sets it: the
run prints the package plan and changes nothing. The `system` tag selects
every role that came from the former `system` role, plus the makepkg tasks of
`package_manager`. The roles also have finer tags of their own, listed in
their README; `make tags` prints them all.

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

## obs.yml

An OBS-only profile for a machine that should get OBS and nothing else. It
runs the `packages` role with `22_obs` plus the GPU groups detected by `lspci`,
then the `obs` role, and skips every other role.

- It requires Arch Linux or CachyOS: the OBS packages are only defined there.
- `packages_state_merge_selection: true` adds these groups to the saved
  selection of the workstation instead of replacing it.
- It refuses `packages_action=reconcile`, which would treat every other
  managed package as obsolete. This check runs before the facts are gathered.
  Reconcile with `site.yml` instead.
- A selected `*-dkms` package also brings the headers of the running kernel;
  the package that owns `/usr/lib/modules/<kernel>/vmlinuz` names them (for
  example `linux-zen-headers`).

```sh
make deploy PLAYBOOK=obs BECOME_PASS=1
```

`make install-obs` is the same command.
