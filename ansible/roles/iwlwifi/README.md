# iwlwifi

Writes the Intel Wi-Fi module options a host lists to
`/etc/modprobe.d/iwlwifi.conf`.

## Requirements

- Privilege escalation (`become: true`).
- `power_save_wifi` false, since the `power_save` role would write the same
  options.

## Role Variables

| Variable                       | Default                            | Description                                                   |
| :----------------------------- | :--------------------------------- | :------------------------------------------------------------ |
| `iwlwifi_module_options`       | `null`                             | List of `module` and `options`. `null` leaves the file alone. |
| `iwlwifi_modprobe_path`        | `/etc/modprobe.d/iwlwifi.conf`     | Options file.                                                 |
| `iwlwifi_vendor_modprobe_path` | `/usr/lib/modprobe.d/iwlwifi.conf` | Packaged file that `iwlwifi_modprobe_path` would hide.        |
| `iwlwifi_module_directory`     | `/sys/module`                      | Where the loaded `iwlwifi` module is detected.                |

Only `iwlwifi`, `iwlmvm` and `iwldvm` are accepted, each at most once, with
options written as `name=value`. An invalid entry fails the run.

```yaml
iwlwifi_module_options:
  - module: iwlmvm
    options: [power_scheme=1]
```

The role writes the file only when `iwlwifi` is loaded, and keeps a backup of
the file it replaces. An empty list removes the file. The run fails rather
than hide a packaged `/usr/lib/modprobe.d/iwlwifi.conf`.

The options apply after a reboot, or after reloading the modules, which drops
the Wi-Fi link:

```bash
sudo modprobe -r iwlmvm iwldvm iwlwifi && sudo modprobe iwlwifi
```

## Choosing options

Check what a module accepts with `modinfo -p iwlmvm`. A few common ones:

- `iwlmvm power_scheme`: `1` active, `2` balanced (default), `3` low power.
  Use `1` when power saving adds latency or drops on a given access point.
- `iwlwifi power_save`: already `0` by default; only `power_scheme` matters on
  `iwlmvm` adapters.
- `iwlwifi swcrypto=1`, `bt_coex_active=0` and `uapsd_disable`: workarounds
  for specific firmware bugs. They cost CPU, Bluetooth coexistence or nothing
  (U-APSD is already off by default), so add them only to fix a reproduced
  problem.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: iwlwifi
      tags: [iwlwifi]
```

## License

Unlicense

## Author Information

pad
