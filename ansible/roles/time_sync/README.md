# time_sync

Enables and starts systemd-timesyncd, unless another NTP client is already in
use.

## Requirements

- systemd.
- Privilege escalation (`become: true`).

## Role Variables

| Variable                 | Default                                                                             | Description                                    |
| :----------------------- | :---------------------------------------------------------------------------------- | :--------------------------------------------- |
| `time_sync_unit`         | `systemd-timesyncd.service`                                                         | Unit enabled and started.                      |
| `time_sync_alternatives` | `[chronyd.service, chrony.service, ntpd.service, ntpsec.service, openntpd.service]` | NTP clients that leave `time_sync_unit` alone. |

## Behavior

An alternative counts as in use when it is enabled, enabled at runtime, an
alias, or running. The role then prints which one and changes nothing, since
two clients would fight over the clock. When `time_sync_unit` itself is not
installed, the role prints a message and changes nothing.

## Tags

`system` and `time_sync` run the role.

## Dependencies

None. In `site.yml` the role runs after `cpu_power` and before `power_save`.

## Example Playbook

```yaml
- name: Configure the Linux workstations
  hosts: all
  become: true
  roles:
    - role: time_sync
      when: packages_action | default('install') != 'plan'
      tags: [system, time_sync]
```

## License

Unlicense

## Author Information

pad
