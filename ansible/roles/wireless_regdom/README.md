# wireless_regdom

Sets the Wi-Fi regulatory domain, which decides the allowed channels and
transmit power.

## Requirements

- Arch Linux, with `/etc/conf.d/wireless-regdom` from the `wireless-regdb`
  package.
- Privilege escalation (`become: true`).

## Role Variables

| Variable                  | Default                       | Description                                                    |
| :------------------------ | :---------------------------- | :------------------------------------------------------------- |
| `wireless_regdom_country` | `null`                        | ISO 3166-1 alpha-2 country code; `null` leaves the file alone. |
| `wireless_regdom_config`  | `/etc/conf.d/wireless-regdom` | File to edit.                                                  |

The role uncomments `WIRELESS_REGDOM="<code>"` and comments out every other
country. The workstations set `wireless_regdom_country: FR` in
`group_vars/all/main.yml`.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: wireless_regdom
      vars:
        wireless_regdom_country: FR
      tags: [wireless_regdom]
```

## License

Unlicense

## Author Information

pad
