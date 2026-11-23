# package_manager

Configures pacman and makepkg on Arch Linux and CachyOS. It runs before the
`packages` role so that the `multilib` repository is enabled before any
package is installed. Every task is skipped on other distributions.

## Requirements

- Arch Linux or CachyOS.
- Privilege escalation (`become: true`).

## Role Variables

| Variable                                  | Default                                                                  | Description                                                     |
| :---------------------------------------- | :----------------------------------------------------------------------- | :-------------------------------------------------------------- |
| `package_manager_pacman_progress_options` | `['ILoveCandy', 'PrettyProgressBar']` on CachyOS, `['ILoveCandy']` else. | Options added to the `[options]` section of `/etc/pacman.conf`. |

## pacman

The role edits `/etc/pacman.conf` in place with `lineinfile` and keeps a
backup of the previous file. Under `[options]` it sets `Color`, `CheckSpace`,
`ParallelDownloads = 5` and the progress options above.

It enables `multilib` only when the file still contains the stock commented
pair `#[multilib]` and `#Include = /etc/pacman.d/mirrorlist`. A custom
`multilib` block is left alone. When the role does enable it, it then runs a
full `pacman -Syu`, which refreshes the databases and upgrades every installed
package.

## makepkg

When `/usr/bin/makepkg` exists, the role writes
`/etc/makepkg.conf.d/zz-dotfiles.conf`:

```sh
CFLAGS+=" -march=native -mtune=native"
CXXFLAGS+=" -march=native -mtune=native"
MAKEFLAGS="-j$(( ($(nproc) + 1) / 2 ))"
OPTIONS+=( '!debug' )
```

Packages are built for the local CPU with half of the CPU threads and without
separate debug packages. A package built this way may fail on a different CPU,
so do not copy it to another machine.

## Tags

| Tag        | Runs                                                    |
| :--------- | :------------------------------------------------------ |
| `pacman`   | The pacman tasks.                                       |
| `packages` | The pacman tasks, because installation depends on them. |
| `yay`      | The pacman tasks, for the same reason.                  |
| `makepkg`  | The makepkg tasks.                                      |
| `system`   | The makepkg tasks.                                      |

`site.yml` also tags the whole role `package_manager`. See
[Running](../../README.md#running) for how to pass tags.

## Dependencies

None. In `site.yml` this role runs before `packages`.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: package_manager
      when: packages_action | default('install') != 'plan'
      tags: [package_manager]
```

## License

Unlicense

## Author Information

pad
