# gnome_keyring

Unlocks the GNOME keyring at a TTY login through PAM, then starts it for the
session.

## Requirements

- Arch Linux, whose `/etc/pam.d/login` includes `system-local-login`. Debian
  and Fedora configure `pam_gnome_keyring` with their own PAM tools.
- gnome-keyring installed. Without its PAM module the role prints a message
  and changes nothing.
- Privilege escalation (`become: true`).

## Role Variables

| Variable                      | Default                                                                                | Description                                                                                                   |
| :---------------------------- | :------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------ |
| `gnome_keyring_pam_enabled`   | `true`                                                                                 | `false` for a host that logs in through a display manager. `site.yml` reads it to skip the role.              |
| `gnome_keyring_pam_directory` | `/etc/pam.d`                                                                           | PAM directory.                                                                                                |
| `gnome_keyring_pam_service`   | `login`                                                                                | PAM service file to edit.                                                                                     |
| `gnome_keyring_pam_module`    | `/usr/lib/security/pam_gnome_keyring.so`                                               | Module that must exist for the role to run.                                                                   |
| `gnome_keyring_pam_rules`     | `-auth`, `-session` with `auto_start`, `-password` with `use_authtok`, each `optional` | Rules to add, each after the rule of type `auth`, `session` or `password` that includes `system-local-login`. |

## PAM rules

Each rule goes right after the `include system-local-login` rule of its type,
and the role keeps a backup of the service file before a change. The leading
dash makes PAM skip a rule whose module is missing, so removing gnome-keyring
cannot break the login. Automatic unlock needs the keyring password to match
the login password; the `password` rule keeps them in step.

After the change the role reads the file back and reports any rule it could
not add, for example when the `include` line is missing. Check mode skips this
check.

## Tags

`system` and `gnome_keyring` run the role.

## Dependencies

None. In `site.yml` the role runs after `wireless_regdom` and before
`dotfiles`.

## Example Playbook

```yaml
- name: Configure the Linux workstations
  hosts: all
  become: true
  roles:
    - role: gnome_keyring
      when:
        - packages_action | default('install') != 'plan'
        - ansible_facts['os_family'] == 'Archlinux'
        - gnome_keyring_pam_enabled | default(true) | bool
      tags: [system, gnome_keyring]
```

## License

Unlicense

## Author Information

pad
