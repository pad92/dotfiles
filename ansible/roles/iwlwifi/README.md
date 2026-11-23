# iwlwifi

Writes the Intel Wi-Fi module options that a host lists to
`/etc/modprobe.d/iwlwifi.conf`.

## Requirements

- Privilege escalation (`become: true`).
- `power_save_wifi` false when the list is not empty, since the
  [power_save](../power_save/README.md) role would write the same options. The
  run fails otherwise.

## Role Variables

| Variable                       | Default                            | Description                                                   |
| :----------------------------- | :--------------------------------- | :------------------------------------------------------------ |
| `iwlwifi_module_options`       | `null`                             | List of `module` and `options`. `null` leaves the file alone. |
| `iwlwifi_modprobe_path`        | `/etc/modprobe.d/iwlwifi.conf`     | Options file.                                                 |
| `iwlwifi_vendor_modprobe_path` | `/usr/lib/modprobe.d/iwlwifi.conf` | Packaged file that `iwlwifi_modprobe_path` would hide.        |
| `iwlwifi_module_directory`     | `/sys/module`                      | Where the loaded `iwlwifi` module is detected.                |

External variable:

- `power_save_wifi`, from the `power_save` role, read with a `false` default.

```yaml
iwlwifi_module_options:
  - module: iwlmvm
    options: [power_scheme=1]
```

## Behavior

- The list accepts `iwlwifi`, `iwlmvm` and `iwldvm`, each at most once. Each
  `options` value must be a list of `name=value` strings matching
  `^[a-z0-9_]+=[^\s]+$`. An invalid entry fails the run.
- The file is written, with a backup of the previous one, only when `iwlwifi`
  is loaded. Otherwise the run reports that no Intel Wi-Fi hardware was found.
- An empty list removes the file.
- A non-empty list fails the run when `/usr/lib/modprobe.d/iwlwifi.conf`
  exists, because a file of the same name under `/etc` would hide it. Review
  its options and choose another `iwlwifi_modprobe_path`.

The handler only prints a reminder. The options apply after a reboot, or after
reloading the modules, which drops the Wi-Fi link:

```bash
sudo modprobe -r iwlmvm iwldvm iwlwifi && sudo modprobe iwlwifi
```

## Choosing options

Check what a module accepts with `modinfo -p iwlmvm`. The kernel defaults below
come from the driver and may change between kernel versions:

- `iwlmvm power_scheme`: `1` active, `2` balanced (default), `3` low power.
  Use `1` when power saving adds latency or drops the link on a given access
  point.
- `iwlwifi power_save`: `0` by default. On `iwlmvm` adapters, `power_scheme`
  sets the behavior.
- `iwlwifi swcrypto=1`, `bt_coex_active=0` and `uapsd_disable`: workarounds for
  specific firmware bugs. The first costs CPU and the second Bluetooth
  coexistence. U-APSD is already off by default. Add them only to fix a
  reproduced problem.

## Tags

`site.yml` tags the role `system` and `iwlwifi`.

## Dependencies

None. In `site.yml` it runs after `power_save`.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: iwlwifi
      when: packages_action | default('install') != 'plan'
      tags: [system, iwlwifi]
```

## License

Unlicense

## Author Information

pad
