# Playbooks

`site.yml` is the only playbook. It holds one play that targets `hosts: all`
with `become: true` and `gather_facts: false`, and applies the
[roles](README.md#roles) from packages to system settings to the home
directory. `make deploy` runs all of it, and `make deploy TAGS=obs` runs the
[OBS profile](#obs-profile). The [Ansible guide](README.md) covers the
inventory, `host_vars` and `group_vars`, and the `make` targets. Each role's
README documents its variables.

## Pre-tasks

The `pre_tasks` are tagged `always`, so they run before any role whatever tags
you pass:

1. With the OBS profile only, an assert refuses `packages_action=reconcile`.
   It checks an argument, not the host, so it runs before the facts are
   gathered.
2. `tasks/target.yml` gathers the facts with `ansible.builtin.setup` as the
   SSH user (`become: false`), so `user_id`, `user_dir` and `env` describe
   the account whose home the roles configure. It then runs the
   [hostname check](README.md#hostname-check).
3. With the OBS profile only, an assert requires Arch Linux or CachyOS.
4. An assert requires a supported distribution: Arch Linux or CachyOS,
   Debian, Ubuntu or Fedora.
5. `ansible.builtin.include_role` runs the `selection` tasks of the `packages`
   role. This step reads the host without changing it and sets
   `packages_selected_groups` for the roles that need it.

## Roles

The play runs with `become: true`. The three home roles (`dotfiles`, `audio`,
`agent_cli`) set `become: false` and run as the SSH user.

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

"not `plan`" means `packages_action` is not `plan`. `make plan` sets it. The
`packages` role then prints the package plan and ends the play with
`ansible.builtin.meta: end_play`, so no later role runs. That is why
`dotfiles`, `agent_cli` and `obs` have no plan condition, and why `make plan`
refuses tags: a tag selection that skips `packages` would skip that stop.
`vpn` reads `packages_host_groups` when `packages_selected_groups` is not
defined.

## Tags

Each role has a tag named after it, except `print3d`, whose tag is `3dprint`
(a role name cannot start with a digit). Two group tags cover several roles:
`system` runs the host roles from `lact` to `gnome_keyring`, and `dotfiles`
runs the three home roles. The `pre_tasks` are tagged `always`. `make tags`
prints every tag.

Some roles also tag part of their tasks. These finer tags are listed in the
role READMEs:

| Tag                                        | Role              | Tasks                                                                         |
| :----------------------------------------- | :---------------- | :---------------------------------------------------------------------------- |
| `pacman`                                   | `package_manager` | Configure `/etc/pacman.conf`. The tasks also carry `packages` and `yay`.      |
| `makepkg`                                  | `package_manager` | Configure native Arch builds. The tasks also carry `system`.                  |
| `yay`                                      | `packages`        | Configure pacman and run the AUR flow only.                                   |
| `kernel_hardening`, `ssh_client_hardening` | `hardening`       | Apply the desktop sysctls, or the SSH client defaults.                        |
| `dotfiles_deploy`                          | `dotfiles`        | Deploy the configuration and the pinned Vim and Zsh plugins.                  |
| `systemd`                                  | `dotfiles`        | Deploy user units and enable the units in `dotfiles_systemd_graphical_units`. |
| `hyprlock_carousel`                        | `dotfiles`        | Render the lock-screen carousel helper.                                       |
| `dotfiles_claude`                          | `agent_cli`       | Configure Claude Code when `claude` is installed, and RTK.                    |
| `dotfiles_rtk`                             | `agent_cli`       | Install RTK and merge its Claude Code hook (`agent_cli_rtk_enabled`).         |
| `dotfiles_codex`                           | `agent_cli`       | Set the Codex status line when `codex` is installed.                          |
| `obs_config`, `obs_virtualcam`             | `obs`             | Configure OBS, or its virtual camera.                                         |

Because the `pacman` tasks also carry `packages`, `make deploy TAGS=packages`
configures pacman before it installs anything, and `makepkg` runs with the
`system` tag.

## Handlers

Roles notify their handlers when a task changes something. Each notified
handler runs once, after all the roles of the play, unless a role flushes them
earlier with `ansible.builtin.meta: flush_handlers` (`dns` and the user units
of `dotfiles` do). Most of them restart or
reload a service: Mako, Waybar, Hyprland, the audio user services (with the
SwayOSD server), systemd-resolved, LACT, and the active user units whose
definitions changed, after a `daemon-reload`. Others only print what needs a
new login or a reboot, such as a new group membership or new module options.

Service jobs are queued without waiting, so a successful play confirms that
they were submitted, not that the services are healthy. Check
`systemctl --user --failed` afterwards.

## Examples

```sh
make deploy BECOME_PASS=1
make check TAGS=dotfiles
make deploy TAGS=packages,gaming BECOME_PASS=1
make deploy BECOME_PASS=1 ANSIBLE_ARGS="-e packages_action=reconcile"
```

## OBS profile

When `obs` is the only tag, `site.yml` installs OBS and nothing else. The
`packages` role installs `22_obs` and the GPU groups that `lspci` detects,
then the `obs` role configures OBS. The tag selection skips the other roles.
With other tags next to it, `obs` only selects the `packages` and `obs` roles,
and the host's usual package selection applies.

- The profile needs Arch Linux or CachyOS, the only distributions that
  define the OBS packages.
- `packages_state_merge_selection: true` adds these groups to the selection
  saved on the workstation instead of replacing it.
- The profile refuses `packages_action=reconcile`, since every other managed
  package would look obsolete. To reconcile, run without tags.
- When a `*-dkms` package is selected, the headers of the running kernel are
  installed too. Their name comes from the package that owns
  `/usr/lib/modules/<kernel>/vmlinuz`, for example `linux-zen-headers`.

```sh
make deploy TAGS=obs BECOME_PASS=1
```

`make install-obs` runs the same command.
