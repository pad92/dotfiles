# package_services

Enables the services of the selected package groups, adds the regular users to
the groups those packages create, and stops those users from lowering their
nice value below 0.

## Requirements

- `packages_selected_groups`, computed by the group selection of the
  `packages` role (see [Pre-tasks](../../PLAYBOOKS.md#pre-tasks)).
- Privilege escalation (`become: true`).

## Role Variables

| Variable                                | Default                                                               | Description                                                            |
| :-------------------------------------- | :-------------------------------------------------------------------- | :--------------------------------------------------------------------- |
| `package_services_by_group`             | See [Default units](#default-units).                                  | Units to enable and start, by OS family and package group.             |
| `package_services_boot_only`            | `[linux-modules-cleanup.service]`                                     | Units enabled but not started, because they run once at boot.          |
| `package_services_unit_directory`       | `/usr/lib/systemd/system`                                             | Where the unit files are looked up.                                    |
| `package_services_device_requirements`  | `bluetooth.service`: `path: /sys/class/bluetooth`, `patterns: [hci*]` | Units enabled only when an entry matching `patterns` exists in `path`. |
| `package_services_user_groups_by_group` | `Archlinux`: `25_razer: [plugdev]`                                    | System groups that the users join, by OS family and package group.     |
| `package_services_retired_user_groups`  | `Archlinux: [realtime]`                                               | Groups the users leave, by OS family, whatever the package groups.     |
| `package_services_nice_limits_file`     | `/etc/security/limits.d/90-no-negative-nice.conf`                     | File that sets a lowest nice value of 0 for the users.                 |
| `package_services_group_users`          | `["{{ ansible_facts['user_id'] }}"]`                                  | Users added to or removed from those groups: the SSH user.             |

### Default units

On Arch Linux:

| Group                  | Units                                                                                  |
| :--------------------- | :------------------------------------------------------------------------------------- |
| `01_base`              | `bluetooth.service`, `fstrim.timer`, `linux-modules-cleanup.service`, `paccache.timer` |
| `04_printers`          | `cups.socket`                                                                          |
| `11_hyprland`          | `swayosd-libinput-backend.service`                                                     |
| `12_containers_docker` | `docker.socket`                                                                        |
| `20_apps`              | `fwupd-refresh.timer`                                                                  |

Debian and Fedora packages usually enable their own services, so the role
lists none for them.

`fstrim.timer` trims the mounted filesystems once a week. `paccache.timer` keeps
the last three versions of each package in the pacman cache.
`swayosd-libinput-backend.service` reads Caps Lock from libinput for the SwayOSD
pop-up.

During a kernel upgrade, the pacman hook of `kernel-modules-hook` keeps the
running kernel's modules, so `modprobe` still works until the reboot. At boot,
`linux-modules-cleanup.service` moves that copy to `/usr/lib/modules/.old`,
which `systemd-tmpfiles` empties after four weeks. The role enables this unit
without starting it, because a oneshot unit that has already run is inactive
and starting it on every deploy would run it again.

## Groups and nice limits

`plugdev` is joined when `25_razer` is selected. `openrazer-driver-dkms` creates
the group, its udev rule gives it the Razer device nodes, and
`openrazer-daemon` does not start for a user outside it.

The users do not join `realtime`, and a user that an older deploy added to it
leaves it. Its limits let any process of the user lower its nice value.
Chromium, and so Electron apps such as Claude Desktop, then raise their display
threads to -8, and every process they start inherits that value. A heavy job
started from such an app then takes the CPU from a Teams call in Firefox
(nice 0), whose voice crackles and speeds up. PipeWire gets real-time
scheduling from rtkit, which `01_base` installs.

Leaving `realtime` is not enough, because `cachyos-settings` gives the `audio`
group a nice limit of -11. The role therefore writes
`package_services_nice_limits_file` with one `<user> - nice 0` line per user.
`pam_limits` gives a user line priority over a group line, so no group can
lower their nice value. The role creates `/etc/security/limits.d` (mode `0755`)
when no package has.

## Behavior

- A unit whose file is missing is reported instead of enabled. An enabled unit
  stays enabled.
- `bluetooth.service` is skipped, with a message, when the host has no
  Bluetooth controller (no `hci*` entry in `/sys/class/bluetooth`).
- `package_services_group_users` must list non-empty names other than `root`,
  or the run fails.
- A group that does not exist yet is reported.
- A user in a retired group leaves it and keeps their other groups. A retired
  group is never joined, even when a package group lists it.

The three handlers only print a message. Log in again for a new group to apply.
After leaving a group or after a change to the nice limit, close every session
or reboot, since the systemd user manager keeps the limits it started with.

The `ananicy-cpp` restart after a change to `cachyos-ananicy-rules` lives in
the [gaming](../gaming/README.md) role.

## Dependencies

None. In `site.yml` it runs after `packages`, `lact` and `gaming`.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: package_services
      when:
        - packages_action | default('install') != 'plan'
        - packages_selected_groups is defined
      tags: [system, package_services]
```

## License

Unlicense

## Author Information

pad
