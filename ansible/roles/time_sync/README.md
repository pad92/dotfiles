# time_sync

Enables and starts systemd-timesyncd, unless another NTP client is already in
use.

## Requirements

- systemd.
- Privilege escalation (`become: true`).

## Role Variables

| Variable                 | Default                                             | Description                                    |
| :----------------------- | :-------------------------------------------------- | :--------------------------------------------- |
| `time_sync_unit`         | `systemd-timesyncd.service`                         | Unit enabled and started.                      |
| `time_sync_alternatives` | chronyd, chrony, ntpd, ntpsec and openntpd services | NTP clients that leave `time_sync_unit` alone. |

When one of `time_sync_alternatives` is enabled or running, the role changes
nothing: two clients would fight over the clock.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: time_sync
      tags: [time_sync]
```

## License

Unlicense

## Author Information

pad
