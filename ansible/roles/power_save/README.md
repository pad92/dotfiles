# power_save

Writes power-saving options for the audio codec modules on a portable machine,
and for the Intel Wi-Fi modules when `power_save_wifi` is true. The options
take effect at the next boot.

## Requirements

- Privilege escalation (`become: true`).

## Role Variables

| Variable                           | Default                                                                                      | Description                                                                          |
| :--------------------------------- | :------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------- |
| `power_save_mode`                  | `auto`                                                                                       | `auto` applies on a portable chassis only. `true` or `false` forces it.              |
| `power_save_wifi`                  | `false`                                                                                      | Also write the Intel Wi-Fi options. See [Wi-Fi](#wi-fi).                             |
| `power_save_portable_form_factors` | See below.                                                                                   | DMI chassis types that count as portable.                                            |
| `power_save_module_directory`      | `/sys/module`                                                                                | Where loaded modules are detected.                                                   |
| `power_save_modprobe_directory`    | `/etc/modprobe.d`                                                                            | Directory scanned for module options that other files set.                           |
| `power_save_modprobe_path`         | `/etc/modprobe.d/power-save.conf`                                                            | Options file.                                                                        |
| `power_save_legacy_modprobe_paths` | `/etc/modprobe.d/zz-dotfiles-power-save.conf`, `/etc/modprobe.d/00-dotfiles-power-save.conf` | Earlier names of the options file, removed on every run.                             |
| `power_save_module_options`        | See [Module groups](#module-groups).                                                         | Audio options per loaded module, by group.                                           |
| `power_save_wifi_module_options`   | See [Module groups](#module-groups).                                                         | Wi-Fi options per loaded module, by group, used only when `power_save_wifi` is true. |

`power_save_portable_form_factors` defaults to Portable, Laptop, Notebook, Sub
Notebook, Hand Held, Convertible, Detachable and Tablet. The role compares them
with the `form_factor` fact.

`power_save_mode` must be `auto`, `true` or `false`, and `power_save_wifi` a
boolean, or the run fails.

## Module groups

Within a group, only the first loaded module gets its options:

| List                             | Modules                           | Options                                                   |
| :------------------------------- | :-------------------------------- | :-------------------------------------------------------- |
| `power_save_module_options`      | `snd_hda_intel`, `snd_ac97_codec` | `power_save=1`                                            |
| `power_save_wifi_module_options` | `iwlwifi`                         | `power_save=1 uapsd_disable=0`                            |
| `power_save_wifi_module_options` | `iwlmvm`, `iwldvm`                | `power_scheme=3` for `iwlmvm`, `force_cam=0` for `iwldvm` |

The Wi-Fi groups live in a separate list, so overriding the audio list cannot
enable them while `power_save_wifi` is false.

A module that another `.conf` file in `power_save_modprobe_directory` already
sets is left out, and the run lists it under "Left to the local modprobe
files". modprobe keeps the last options line it reads, so file order alone
would not let a local file win. Dashes and underscores in module names count
as the same character.

The file is removed when power saving does not apply, when none of the listed
modules is loaded, or when other files configure every selected module. The
handler only prints a reminder to reboot or reload the modules.

On a desktop, the latency that power saving adds costs more than the energy it
saves, hence the `auto` default.

## Wi-Fi

Wi-Fi power saving is off by default. With U-APSD, `power_save=1` can crash the
Intel firmware ("Queue stuck", "Microcode SW error") and break DNS and
connectivity. Enable it only on hardware known to be stable.

To set Intel Wi-Fi options by hand, use the [iwlwifi](../iwlwifi/README.md)
role. It refuses to run while `power_save_wifi` is true, and this role leaves
alone any module that `iwlwifi.conf` already sets.

## Tags

`site.yml` tags the role `system` and `power_save`.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: power_save
      when: packages_action | default('install') != 'plan'
      tags: [system, power_save]
```

## License

Unlicense

## Author Information

pad
