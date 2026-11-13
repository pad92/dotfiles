# cpu_power

Applies the AMD P-State energy preference (EPP) and the X3D CCD mode, and
restores them at boot.

## Requirements

- An AMD CPU with AMD P-State in active mode, read from the facts and from the
  controls the kernel exposes. Other CPUs are left alone.
- Privilege escalation (`become: true`).

## Role Variables

| Variable                      | Default                                 | Description                                                                                                   |
| :---------------------------- | :-------------------------------------- | :------------------------------------------------------------------------------------------------------------ |
| `cpu_power_amd_pstate_epp`    | `balance_performance`                   | EPP value. `null` disables EPP management.                                                                    |
| `cpu_power_amd_x3d_mode`      | `null`                                  | `cache` or `frequency`; `null` leaves the X3D mode unchanged.                                                 |
| `cpu_power_amd_tmpfiles_path` | `/etc/tmpfiles.d/dotfiles-amd-cpu.conf` | Boot-time copy of the applied settings.                                                                       |
| `cpu_power_managers`          | see `defaults/main.yml`                 | Power managers that take over EPP: power-profiles-daemon, auto-cpufreq, TLP, tuned, cpupower, system76-power. |

## Behavior

The role selects the `powersave` governor, then applies the EPP value. Both
must be available on the CPU policy. With `powersave`, EPP guides the
performance and energy balance.

EPP is not changed while a power manager of `cpu_power_managers` is active or
enabled, which keeps its profile, including a game's temporary performance
profile. The X3D mode changes only when `cpu_power_amd_x3d_mode` is set and the
kernel exposes the control; choose it for the host's workloads. Core
Performance Boost and the kernel boot parameters are never changed.

The applied settings are written to `cpu_power_amd_tmpfiles_path`, so
`systemd-tmpfiles` restores them at boot: governor, then EPP, then X3D mode.
EPP lines are written only while no power manager is active or enabled. The
file is removed when the role no longer manages any of these controls. See the
[CachyOS CPU tuning guide](https://wiki.cachyos.org/fr/configuration/general_system_tweaks/)
for firmware requirements.

Tags: `cpu_power`, `amd_cpu_performance`.

```sh
make deploy TAGS=amd_cpu_performance BECOME_PASS=1
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: cpu_power
      tags: [cpu_power]
```

## License

Unlicense

## Author Information

pad
