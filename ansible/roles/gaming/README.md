# gaming

Configures the services of the `21_steam` package group: `ananicy-cpp`, and
power-profiles-daemon as the only CPU power manager.

## Requirements

- Arch Linux or CachyOS, with `21_steam` selected. `site.yml` runs the role
  only then.
- The packages of `packages_gaming_required_packages` installed. The role
  checks them first and does not install them: run the `packages` tag for
  that.
- Privilege escalation (`become: true`).

## Role Variables

| Variable                               | Default                             | Description                                                                                 |
| :------------------------------------- | :---------------------------------- | :------------------------------------------------------------------------------------------ |
| `gaming_power_manager_conflict_action` | `ask`                               | Another CPU power manager is running: `ask`, `remove` (stop, disable, uninstall) or `fail`. |
| `gaming_ananicy_rule_packages`         | `[cachyos-ananicy-rules]`           | Packages whose update restarts `ananicy-cpp` so it loads the new rules.                     |
| `gaming_sched_ext_units`               | `[scx_loader.service, scx.service]` | sched-ext units stopped, disabled and masked.                                               |

## Behavior

The role enables and starts `ananicy-cpp` and `power-profiles-daemon`. If
auto-cpufreq, TLP, tuned or another known CPU power manager is active or
enabled, it asks whether to stop, disable and uninstall it, and stops if you
decline. Check mode never removes anything. Once the check passes, a systemd
mask on `power-profiles-daemon.service` is removed before it is enabled. A
running `ananicy-cpp` keeps running.

`ananicy-cpp` and a sched-ext scheduler both change how processes are
scheduled, and the
[CachyOS wiki](https://wiki.cachyos.org/configuration/sched-ext/) advises
against running both. The role therefore stops, disables and masks the
installed units of `gaming_sched_ext_units`. `scx_loader` starts on D-Bus
demand, so the mask also stops scx-manager from starting it. To use a sched-ext
scheduler instead, set `gaming_sched_ext_units: []` and run
`sudo systemctl unmask scx_loader.service`.

Deselecting Steam does not stop the services.

### Related settings

- The `hardening` role raises `vm.max_map_count` for Proton games.
- The `steam-optimize` launcher (deployed by `dotfiles`) uses
  `game-performance` on CachyOS. It sets a 12 GB Mesa shader cache on AMD or a
  12 GB proprietary-driver cache on NVIDIA; game profiles can override them,
  and Arc Raiders uses 20 GB. It reads the most recent account from
  `loginusers.vdf`, and falls back to the only `localconfig.vdf` when there is
  exactly one.
- Avoid `gamemoderun` while `ananicy-cpp` runs: both change process
  priorities
  ([CachyOS gaming guide](https://wiki.cachyos.org/fr/configuration/gaming/)).
  `ENABLE_LAYER_MESA_ANTI_LAG` stays a per-game option.

```sh
make deploy TAGS=packages,gaming BECOME_PASS=1
```

## Dependencies

None. The `packages` role installs the services it configures.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: gaming
      when: "'21_steam' in packages_selected_groups"
      tags: [gaming]
```

## License

Unlicense

## Author Information

pad
