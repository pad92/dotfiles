# power_save

Writes the audio power-saving module options on a portable machine, and the
Wi-Fi ones when `power_save_wifi` is true.

## Requirements

- Privilege escalation (`become: true`).

## Role Variables

| Variable                           | Default                                       | Description                                                                             |
| :--------------------------------- | :-------------------------------------------- | :-------------------------------------------------------------------------------------- |
| `power_save_mode`                  | `auto`                                        | `auto` applies on a portable chassis only; `true` or `false` forces it.                 |
| `power_save_wifi`                  | `false`                                       | Also write the Intel Wi-Fi options. Off by default: they can crash the Intel firmware.  |
| `power_save_portable_form_factors` | Portable, Laptop, Notebook, Convertible...    | DMI chassis types that count as portable.                                               |
| `power_save_module_directory`      | `/sys/module`                                 | Where loaded modules are detected.                                                      |
| `power_save_modprobe_path`         | `/etc/modprobe.d/00-dotfiles-power-save.conf` | Module options file. It sorts first, so any local module file overrides it.             |
| `power_save_legacy_modprobe_paths` | `zz-dotfiles-power-save.conf`                 | Earlier file names, removed at each run.                                                |
| `power_save_module_options`        | see below                                     | Audio options per loaded module, by group.                                              |
| `power_save_wifi_module_options`   | see below                                     | Wi-Fi options per loaded module, by group, applied only when `power_save_wifi` is true. |

Within a group, only the first loaded module gets its options:

| List                             | Group                             | Options                                         |
| :------------------------------- | :-------------------------------- | :---------------------------------------------- |
| `power_save_module_options`      | `snd_hda_intel`, `snd_ac97_codec` | `power_save=1`                                  |
| `power_save_wifi_module_options` | `iwlwifi`                         | `power_save=1 uapsd_disable=0`                  |
| `power_save_wifi_module_options` | `iwlmvm`, `iwldvm`                | `power_scheme=3`, or `force_cam=0` for `iwldvm` |

The file is removed when power saving does not apply. The options take effect
at the next boot. On a desktop, battery life matters less than the latency
power saving adds.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: power_save
      tags: [power_save]
```

## License

Unlicense

## Author Information

pad
