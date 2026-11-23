# wireless_regdom

Sets the Wi-Fi regulatory domain, which decides the allowed channels and
transmit power.

## Requirements

- Arch Linux, with `/etc/conf.d/wireless-regdom` from the `wireless-regdb`
  package. Without the file the role prints a message and changes nothing.
- Privilege escalation (`become: true`).

## Role Variables

| Variable                  | Default                       | Description                                                                                  |
| :------------------------ | :---------------------------- | :------------------------------------------------------------------------------------------- |
| `wireless_regdom_country` | `null`                        | ISO 3166-1 alpha-2 country code, or `00` for the world domain. `null` leaves the file alone. |
| `wireless_regdom_config`  | `/etc/conf.d/wireless-regdom` | File to edit.                                                                                |

The workstations set `wireless_regdom_country: FR` in
`group_vars/all/main.yml`.

## Behavior

The role refuses a code that is not two uppercase letters or `00`. It
uncomments `WIRELESS_REGDOM="<code>"`, comments out every other country, and
keeps a backup of the file before a change. The new domain applies at the next
boot, or at once with `iw reg set <code>`.

## Tags

`system` and `wireless_regdom` run the role.

## Dependencies

None. In `site.yml` the role runs after `iwlwifi` and before `gnome_keyring`.

## Example Playbook

```yaml
- name: Configure the Linux workstations
  hosts: all
  become: true
  roles:
    - role: wireless_regdom
      when:
        - packages_action | default('install') != 'plan'
        - ansible_facts['os_family'] == 'Archlinux'
      tags: [system, wireless_regdom]
```

## License

Unlicense

## Author Information

pad
