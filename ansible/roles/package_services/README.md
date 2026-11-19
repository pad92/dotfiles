# package_services

Enables the services of the selected package groups and adds the regular
users to the groups those packages create.

## Requirements

- `packages_selected_groups`, computed by the playbook's group selection.
- Privilege escalation (`become: true`).

## Role Variables

| Variable                                | Default                          | Description                                                        |
| :-------------------------------------- | :------------------------------- | :----------------------------------------------------------------- |
| `package_services_by_group`             | see below                        | Units to enable and start, by OS family and package group.         |
| `package_services_device_requirements`  | `bluetooth.service` needs `hci*` | Units enabled only when a matching entry exists under `path`.      |
| `package_services_user_groups_by_group` | see below                        | System groups that the users join, by OS family and package group. |
| `package_services_retired_user_groups`  | `realtime` on Arch Linux         | Groups the users leave, by OS family, whatever the package groups. |
| `package_services_group_users`          | the SSH user                     | Users added to those groups, or removed from the retired ones.     |
| `package_services_unit_directory`       | `/usr/lib/systemd/system`        | Where the unit files are looked up.                                |

Default units on Arch Linux:

| Group                  | Units                                                 |
| :--------------------- | :---------------------------------------------------- |
| `01_base`              | `bluetooth.service`, `fstrim.timer`, `paccache.timer` |
| `04_printers`          | `cups.socket`                                         |
| `12_containers_docker` | `docker.socket`                                       |
| `20_apps`              | `fwupd-refresh.timer`                                 |

`fstrim.timer` trims the mounted filesystems once a week. `paccache.timer`
keeps the last three versions of each package in the pacman cache. Debian and
Fedora packages usually enable their own services.

Default group on Arch Linux: `plugdev` with `25_razer`, which OpenRazer's udev
rule gives the device.

The user does not join `realtime`, and a user that an older deploy added to it
leaves it. Its limits let any process of the user
lower its nice value. Chromium, and so Electron apps such as Claude Desktop,
then raise their display threads to -8, and every process they start inherits
that value. A heavy job started from such an app then takes the CPU from a
Teams call in Firefox (nice 0), whose voice crackles and speeds up. PipeWire
gets real-time scheduling from rtkit, which `01_base` installs.

## Behavior

A unit whose file is missing is reported instead of enabled. An enabled unit
stays enabled. `bluetooth.service` is skipped, with a message, when the host
has no Bluetooth controller (no `hci*` entry in `/sys/class/bluetooth`). A
group that does not exist yet is reported. A user in a retired group leaves it
and keeps their other groups. Log in again for a group change to apply.

When the play installs or updates `cachyos-ananicy-rules`, the role restarts
`ananicy-cpp` so the new rules load.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: package_services
      tags: [package_services]
```

## License

Unlicense

## Author Information

pad
