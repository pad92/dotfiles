# power_save

Writes the Wi-Fi and audio power-saving module options on a portable machine.

## Requirements

- Privilege escalation (`become: true`).

## Role Variables

| Variable                           | Default                                       | Description                                                             |
| :--------------------------------- | :-------------------------------------------- | :---------------------------------------------------------------------- |
| `power_save_mode`                  | `auto`                                        | `auto` applies on a portable chassis only; `true` or `false` forces it. |
| `power_save_portable_form_factors` | Portable, Laptop, Notebook, Convertible...    | DMI chassis types that count as portable.                               |
| `power_save_module_directory`      | `/sys/module`                                 | Where loaded modules are detected.                                      |
| `power_save_modprobe_path`         | `/etc/modprobe.d/zz-dotfiles-power-save.conf` | Module options file.                                                    |
| `power_save_module_options`        | see below                                     | Options per loaded module, by group.                                    |

Within a group, only the first loaded module gets its options:

| Group                             | Options                                         |
| :-------------------------------- | :---------------------------------------------- |
| `iwlwifi`                         | `power_save=1 uapsd_disable=0`                  |
| `iwlmvm`, `iwldvm`                | `power_scheme=3`, or `force_cam=0` for `iwldvm` |
| `snd_hda_intel`, `snd_ac97_codec` | `power_save=1`                                  |

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
