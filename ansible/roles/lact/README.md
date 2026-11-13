# lact

Writes the LACT GPU profiles to `/etc/lact/config.yaml` for the GPUs that LACT
reports.

## Requirements

- `lactd.service` installed. Without it the role changes nothing.
- A running LACT daemon in check mode, which it needs to list the GPUs.
- Privilege escalation (`become: true`).

## Role Variables

| Variable               | Default                 | Description                                                                                              |
| :--------------------- | :---------------------- | :------------------------------------------------------------------------------------------------------- |
| `lact_config_path`     | `/etc/lact/config.yaml` | LACT daemon configuration.                                                                               |
| `lact_profiles`        | see `defaults/main.yml` | AMD profiles: `auto` performance level for `Auto` and `Adaptive`, `high` for `PreferMaximumPerformance`. |
| `lact_nvidia_profiles` | see `defaults/main.yml` | NVIDIA profiles, each set to the PowerMizer mode of the same name.                                       |

## Behavior

The role reads the GPU identifiers and drivers from LACT, then creates the
missing `Auto`, `Adaptive` and `PreferMaximumPerformance` profiles for AMD and
NVIDIA GPUs. These names match LACT's NVIDIA PowerMizer modes. Profiles do not
override fan control. Intel GPUs keep their settings.

Existing `Balance`, `Silence`, `Performance` and `Jeux-perf` profiles are
renamed. Their settings move to the new name when it is unused; an existing
profile with the new name wins. The current selection follows the rename.
Defaults fill only the missing GPU entries of existing profiles; other
settings and automation are kept. With no named profile, `Auto` becomes
active.

Identifier casing is repaired. An unknown GPU or conflicting entries stop the
play before the file is written, and so does a link or a directory at
`lact_config_path`. A changed file is backed up and restarts `lactd`. The
former `~/.config/lact/config.yaml` is left untouched and no longer deployed.

With LACT 0.7.5+ and power-profiles-daemon 0.30+, LACT disables PPD's
conflicting `amdgpu_dpm` action
([LACT documentation](https://github.com/ilya-zlobintsev/LACT#power-profiles-daemon-note)).
Check `powerprofilesctl list-actions` and `journalctl -u lactd -b` after a
deployment.

```sh
make deploy TAGS=lact BECOME_PASS=1
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: lact
      tags: [lact]
```

## License

Unlicense

## Author Information

pad
