# gaming

Configures the services of the `21_steam` package group: `ananicy-cpp`, and
power-profiles-daemon as the only CPU power manager.

## Requirements

- Arch Linux or CachyOS, with `21_steam` selected. `site.yml` runs the role
  only then.
- The packages of `packages_gaming_required_packages` (`packages` role)
  installed. The role checks them and does not install them: a missing package
  fails the run, and check mode only reports it.
- Privilege escalation (`become: true`).

## Role Variables

| Variable                               | Default                             | Description                                                                                           |
| :------------------------------------- | :---------------------------------- | :---------------------------------------------------------------------------------------------------- |
| `gaming_power_manager_conflict_action` | `ask`                               | Another CPU power manager is active or enabled: `ask`, `remove` (stop, disable, uninstall) or `fail`. |
| `gaming_ananicy_rule_packages`         | `[cachyos-ananicy-rules]`           | Packages whose install or update in the same run restarts `ananicy-cpp`, so it loads the new rules.   |
| `gaming_sched_ext_units`               | `[scx_loader.service, scx.service]` | sched-ext units stopped, disabled and masked.                                                         |

External variable:

- `packages_changed_this_run`, set by the `packages` role, triggers the
  `ananicy-cpp` restart.

## CPU power manager

The role reads which CPU power managers are active or enabled with the
`power_manager_facts` tasks of the [cpu_power](../cpu_power/README.md) role.
When one other than power-profiles-daemon is found, `ask` prompts `[y/N]`.
Answering yes, or setting `remove`, stops and disables the units and uninstalls
the packages that own their unit files (`pacman -Qqo`). A unit that no package
owns is only stopped and disabled. Declining, or `fail`, ends the run on the
"Require a single CPU power manager" check. Check mode never removes anything.

Once the check passes, the role removes a systemd mask on
`power-profiles-daemon.service`, then enables and starts it with
`ananicy-cpp`. A running `ananicy-cpp` is restarted only when a package of
`gaming_ananicy_rule_packages` changed in this run.

## sched-ext schedulers

`ananicy-cpp` and a sched-ext scheduler both change how processes are
scheduled, and the
[CachyOS wiki](https://wiki.cachyos.org/configuration/sched-ext/) advises
against running both. The role stops, disables and masks the installed units of
`gaming_sched_ext_units`. `scx_loader` starts on D-Bus demand, so the mask also
stops scx-manager from starting it. To use a sched-ext scheduler instead, set
`gaming_sched_ext_units: []` and run
`sudo systemctl unmask scx_loader.service`.

Deselecting Steam does not stop the services.

## Related settings

- The [hardening](../hardening/README.md) role raises `vm.max_map_count` for
  Proton games.
- The `steam-optimize` launcher, deployed by `dotfiles`, uses
  `game-performance` on CachyOS when it is installed. It sets a 12 GB shader
  cache for Mesa (AMD) or the NVIDIA driver, and game profiles can raise it.
  `steam-optimize -i` writes the launch options of a game, including a
  per-game mouse DPI (`--dpi <N>`) that needs `razer-cli` from `25_razer`. On a
  monitor that Hyprland reports as HDR capable, it runs Gamescope with
  `--hdr-enabled` and switches the monitor to HDR only while the game runs.
  `--no-hdr` keeps a game in SDR.
- Avoid `gamemoderun` while `ananicy-cpp` runs, since both change process
  priorities
  ([CachyOS gaming guide](https://wiki.cachyos.org/fr/configuration/gaming/)).
  `ENABLE_LAYER_MESA_ANTI_LAG` stays a per-game option.

To install the packages and configure the services in one run, pass the
`packages` and `gaming` tags (see [Running](../../README.md#running)).

## Tags

`site.yml` tags the role `system` and `gaming`. The tasks have no tags of their
own.

## Dependencies

None. The `packages` role installs the services it configures and runs before
it in `site.yml`.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: gaming
      when:
        - packages_action | default('install') != 'plan'
        - ansible_facts["os_family"] == "Archlinux"
        - "'21_steam' in (packages_selected_groups | default([]))"
      tags: [system, gaming]
```

## License

Unlicense

## Author Information

pad
