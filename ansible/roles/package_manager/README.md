# package_manager

Configures pacman and makepkg on Arch Linux and CachyOS. The `packages` role
installs packages afterwards, so `multilib` is ready before it runs.

## Requirements

- Arch Linux or CachyOS. The tasks skip other distributions.
- Privilege escalation (`become: true`).

## Role Variables

| Variable                                  | Default                                                      | Description                                     |
| :---------------------------------------- | :----------------------------------------------------------- | :---------------------------------------------- |
| `package_manager_pacman_progress_options` | `[ILoveCandy, PrettyProgressBar]` on CachyOS, `[ILoveCandy]` | Progress bar options set in `/etc/pacman.conf`. |

`packages_upgrade_system` (from the `packages` role) is read too: see below.

## pacman

The role sets `Color`, `CheckSpace`, `ParallelDownloads = 5` and the progress
options in `/etc/pacman.conf`, and enables the standard `multilib`
repository. Enabling `multilib` triggers `pacman -Syu`, which synchronizes the
package databases and upgrades the installed packages.

Tags: `pacman`, `pacman_config`. The `packages`, `packages_install`,
`packages_reconcile` and `yay` tags run it too, since installation needs it.

## makepkg

makepkg builds for the local CPU (native flags) without generating separate
debug packages. A package built this way may not run on a different CPU.

Tags: `makepkg`, `makepkg_config`, `system`.

```sh
make deploy TAGS=makepkg BECOME_PASS=1
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: package_manager
      tags: [package_manager]
```

## License

Unlicense

## Author Information

pad
