# lact

Enables the LACT daemon and writes the `Auto`, `Adaptive` and
`PreferMaximumPerformance` GPU profiles to `/etc/lact/config.yaml` for the AMD
and NVIDIA GPUs that LACT reports.

## Requirements

- `lactd.service` installed. The `08_amd` package group installs `lact`.
  Without the unit, the role changes nothing.
- In check mode, a running LACT daemon, since the role cannot start it there
  and needs it to list the GPUs.
- Privilege escalation (`become: true`).

## Role Variables

| Variable               | Default                 | Description                                                                                               |
| :--------------------- | :---------------------- | :-------------------------------------------------------------------------------------------------------- |
| `lact_config_path`     | `/etc/lact/config.yaml` | LACT daemon configuration. It must be a regular file, or absent.                                          |
| `lact_profiles`        | See below.              | AMD profiles: `performance_level: auto` for `Auto` and `Adaptive`, `high` for `PreferMaximumPerformance`. |
| `lact_nvidia_profiles` | See below.              | NVIDIA profiles: each sets `power_mizer_mode` to the profile name.                                        |

The profile names match LACT's NVIDIA PowerMizer modes, and the Waybar
`lact-profile` module deployed by `dotfiles` cycles through them. The defaults
set no fan control, so the fan curves stay as they are.

## Behavior

The role enables and starts `lactd.service`, then reads the GPU identifiers
with `lact cli list` and each driver with `lact cli info`, with a 10-second
timeout on each call. Only GPUs using `amdgpu` or `nvidia` get profiles. When
LACT reports neither, the configuration is left unchanged. Intel GPUs keep
their settings.

The `lact_config` filter (`filter_plugins/lact.py`) then merges the defaults
into the existing file:

- The file must be at `version: 7`, or the run fails.
- Earlier profile names are renamed: `Balance` to `Auto`, `Silence` to
  `Adaptive`, and `Performance` or `Jeux-perf` to `PreferMaximumPerformance`.
  When the new name already exists, that profile is kept and the old one is
  dropped. A `current_profile` that pointed to an old name follows the rename.
- Defaults fill only the missing GPU entries of each profile. Saved per-GPU
  settings and other keys are kept.
- When the file had no profile and no `current_profile`, `Auto` is selected and
  `auto_switch_profiles` is set to `false`.
- GPU identifier casing is corrected to match LACT's output.

The run fails before writing when a GPU in the file is not detected, when two
entries map to the same GPU, when the selected profile does not exist, or when
`lact_config_path` is a link or a directory. The role creates the directory
with mode `0755` and writes the file with mode `0644`. A changed file is backed
up and notifies the `Restart LACT` handler. The former
`~/.config/lact/config.yaml` is no longer deployed, and the role leaves it
alone.

With LACT 0.7.5 or later and power-profiles-daemon 0.30 or later, LACT
disables the conflicting `amdgpu_dpm` action of power-profiles-daemon
([LACT documentation](https://github.com/ilya-zlobintsev/LACT#power-profiles-daemon-note)).
After a deployment, check `powerprofilesctl list-actions` and
`journalctl -u lactd -b`.

## Tags

`site.yml` tags the role `system` and `lact`. See
[Running](../../README.md#running) for how to pass tags.

## Dependencies

None. In `site.yml` it runs after `packages`.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: lact
      when: packages_action | default('install') != 'plan'
      tags: [system, lact]
```

## License

Unlicense

## Author Information

pad
