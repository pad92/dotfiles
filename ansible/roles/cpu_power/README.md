# cpu_power

Applies the AMD P-State energy preference (EPP) and the X3D CCD mode, and
restores them at boot.

## Requirements

- An AMD CPU: the role runs only when the processor facts contain
  `AuthenticAMD`. EPP also needs AMD P-State in active mode.
- Privilege escalation (`become: true`).

## Role Variables

| Variable                      | Default                                 | Description                                                                                       |
| :---------------------------- | :-------------------------------------- | :------------------------------------------------------------------------------------------------ |
| `cpu_power_amd_pstate_epp`    | `balance_performance`                   | `performance`, `balance_performance`, `balance_power` or `power`. `null` disables EPP management. |
| `cpu_power_amd_x3d_mode`      | `null`                                  | `frequency` or `cache`. `null` leaves the X3D mode unchanged.                                     |
| `cpu_power_amd_tmpfiles_path` | `/etc/tmpfiles.d/dotfiles-amd-cpu.conf` | Boot-time copy of the applied settings.                                                           |
| `cpu_power_managers`          | See below.                              | Power managers that own EPP while they are active or enabled.                                     |

`cpu_power_managers` defaults to `power-profiles-daemon.service`,
`auto-cpufreq.service`, `tlp.service`, `tuned.service`, `tuned-ppd.service`,
`cpupower.service` and `system76-power.service`.

Any other value of the first two variables fails the run before a change.

## EPP

EPP is applied only when `/sys/devices/system/cpu/amd_pstate/status` reads
`active` and no power manager of `cpu_power_managers` is active or enabled.
This keeps a power manager's profile, including a game's temporary performance
profile.

For each CPU policy under `/sys/devices/system/cpu/cpufreq`, the role selects
the `powersave` governor, then writes the EPP value. With `powersave`, EPP
guides the balance between performance and energy. Both the governor and the
value must be available on the policy. If a step fails, the role restores the
original governor and EPP of that policy, then fails.

On a host with `21_steam`, the [gaming](../gaming/README.md) role enables
power-profiles-daemon, so this role never sets EPP there.

## X3D mode

The X3D mode changes only when `cpu_power_amd_x3d_mode` is set and the
`amd_x3d_vcache` driver exposes an `amd_x3d_mode` control under
`/sys/bus/platform/drivers/amd_x3d_vcache`. A running power manager does not
block it. Choose the mode for the host's workloads.

Core Performance Boost and the kernel boot parameters are never changed.

## Boot persistence

The settings applied in this run are written to `cpu_power_amd_tmpfiles_path`,
so `systemd-tmpfiles` restores them at boot in this order: governor, EPP, X3D
mode. The file is removed when the run manages none of these controls, for
example once a power manager is enabled. See the
[CachyOS CPU tuning guide](https://wiki.cachyos.org/fr/configuration/general_system_tweaks/)
for firmware requirements.

The `power_manager_facts` tasks, which list the active or enabled power
managers, are also used by the `gaming` role.

## Tags

`site.yml` tags the role `system` and `cpu_power`. The EPP tasks included for
each policy also carry `cpu_power`. See [Running](../../README.md#running) for
how to pass tags.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: cpu_power
      when: packages_action | default('install') != 'plan'
      tags: [system, cpu_power]
```

## License

Unlicense

## Author Information

pad
