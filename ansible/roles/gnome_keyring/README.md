# gnome_keyring

Unlocks the GNOME keyring at a TTY login through PAM, then starts it for the
session.

## Requirements

- Arch Linux, whose `/etc/pam.d/login` includes `system-local-login`. Debian
  and Fedora configure `pam_gnome_keyring` with their own PAM tools.
- gnome-keyring installed. Without it the role changes nothing.
- Privilege escalation (`become: true`).

## Role Variables

| Variable                      | Default                                                 | Description                                                |
| :---------------------------- | :------------------------------------------------------ | :--------------------------------------------------------- |
| `gnome_keyring_pam_enabled`   | `true`                                                  | `false` for a host that logs in through a display manager. |
| `gnome_keyring_pam_directory` | `/etc/pam.d`                                            | PAM directory.                                             |
| `gnome_keyring_pam_service`   | `login`                                                 | PAM service file to edit.                                  |
| `gnome_keyring_pam_module`    | `/usr/lib/security/pam_gnome_keyring.so`                | Module that must exist for the role to run.                |
| `gnome_keyring_pam_rules`     | `-auth`, `-session auto_start`, `-password use_authtok` | Rules to add.                                              |

Each rule goes right after the `include system-local-login` rule of its type.
The leading dash makes PAM skip a rule whose module is missing, so removing
gnome-keyring cannot break the login. Automatic unlock needs the keyring
password to match the login password; the `password` rule keeps them in step.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: gnome_keyring
      tags: [gnome_keyring]
```

## License

Unlicense

## Author Information

pad
