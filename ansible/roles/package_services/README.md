# package_services

Enables the services of the selected package groups, adds the regular users
to the groups those packages create, and stops those users from lowering
their nice value below 0.

## Requirements

- `packages_selected_groups`, computed by the playbook's group selection.
- Privilege escalation (`become: true`).

## Role Variables

| Variable                                | Default                                           | Description                                                        |
| :-------------------------------------- | :------------------------------------------------ | :----------------------------------------------------------------- |
| `package_services_by_group`             | see below                                         | Units to enable and start, by OS family and package group.         |
| `package_services_boot_only`            | `linux-modules-cleanup.service`                   | Units enabled but not started, because they run once at boot.      |
| `package_services_device_requirements`  | `bluetooth.service` needs `hci*`                  | Units enabled only when a matching entry exists under `path`.      |
| `package_services_user_groups_by_group` | see below                                         | System groups that the users join, by OS family and package group. |
| `package_services_retired_user_groups`  | `realtime` on Arch Linux                          | Groups the users leave, by OS family, whatever the package groups. |
| `package_services_group_users`          | the SSH user                                      | Users added to those groups, or removed from the retired ones.     |
| `package_services_nice_limits_file`     | `/etc/security/limits.d/90-no-negative-nice.conf` | Where those users get a lowest nice value of 0.                    |
| `package_services_unit_directory`       | `/usr/lib/systemd/system`                         | Where the unit files are looked up.                                |

Default units on Arch Linux:

| Group                  | Units                                                                                  |
| :--------------------- | :------------------------------------------------------------------------------------- |
| `01_base`              | `bluetooth.service`, `fstrim.timer`, `linux-modules-cleanup.service`, `paccache.timer` |
| `04_printers`          | `cups.socket`                                                                          |
| `11_hyprland`          | `swayosd-libinput-backend.service`                                                     |
| `12_containers_docker` | `docker.socket`                                                                        |
| `20_apps`              | `fwupd-refresh.timer`                                                                  |

`fstrim.timer` trims the mounted filesystems once a week. `paccache.timer`
keeps the last three versions of each package in the pacman cache.
During a kernel upgrade, the pacman hook of `kernel-modules-hook` keeps the
running kernel's modules, so `modprobe` still works until the reboot. At boot,
`linux-modules-cleanup.service` moves that copy to `/usr/lib/modules/.old`,
which `systemd-tmpfiles` empties after four weeks. The role enables this unit
without starting it (`package_services_boot_only`): it runs once per boot.
Debian and Fedora packages usually enable their own services.

Default group on Arch Linux: `plugdev` with `25_razer`, which OpenRazer's udev
rule gives the device.

The user does not join `realtime`, and a user that an older deploy added to it
leaves it. Its limits let any process of the user
lower its nice value. Chromium, and so Electron apps such as Claude Desktop,
then raise their display threads to -8, and every process they start inherits
that value. A heavy job started from such an app then takes the CPU from a
Teams call in Firefox (nice 0), whose voice crackles and speeds up. PipeWire
gets real-time scheduling from rtkit, which `01_base` installs.

Leaving `realtime` is not enough: `cachyos-settings` gives the `audio` group
the same nice limit. The role writes `package_services_nice_limits_file` with
one `<user> - nice 0` line per user; `pam_limits` gives a user line priority
over a group line, so no group can lower their nice value.

## Behavior

A unit whose file is missing is reported instead of enabled. An enabled unit
stays enabled. `bluetooth.service` is skipped, with a message, when the host
has no Bluetooth controller (no `hci*` entry in `/sys/class/bluetooth`). A
group that does not exist yet is reported. A user in a retired group leaves it
and keeps their other groups. A retired group is never joined, even when a
package group lists it. Log in again for a new group to apply; after leaving
one, close every session or reboot, since the systemd user manager keeps the
limits it started with.

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
