# print3d

Installs PrusaSlicer and F3D, and makes F3D's thumbnailers work in Nautilus so
3D files (STL, STEP, 3MF, glTF...) get a preview.

## Requirements

- Arch Linux, with `24_3dprint` selected. `site.yml` runs the role only then,
  and the role stops on any other distribution.
- Privilege escalation (`become: true`).

## Role Variables

| Variable                          | Default                                                                                       | Description                                                      |
| :-------------------------------- | :-------------------------------------------------------------------------------------------- | :--------------------------------------------------------------- |
| `print3d_packages`                | `"{{ packages_family_groups['Archlinux']['24_3dprint'] }}"`                                   | Packages installed with pacman. An empty list skips the install. |
| `print3d_f3d_config_dir`          | `/etc/f3d`                                                                                    | System F3D configuration directory.                              |
| `print3d_f3d_config_owner`        | `root`                                                                                        | Owner of the configuration.                                      |
| `print3d_f3d_config_group`        | `root`                                                                                        | Group of the configuration.                                      |
| `print3d_f3d_thumbnail_options`   | `{rendering-backend: egl}`                                                                    | Options written to `thumbnail.json`.                             |
| `print3d_thumbnail_cache_dir`     | `XDG_CACHE_HOME` from the environment, else `user_dir ~ '/.cache'`, followed by `/thumbnails` | GNOME thumbnail cache of the SSH user.                           |
| `print3d_thumbnail_cache_subdirs` | `[fail, normal, large, x-large, xx-large]`                                                    | Cache directories cleared when the F3D file changes.             |

`print3d_packages` reads `packages_family_groups` from the `packages` role. The
role also reads the `os_family`, `env` and `user_dir` facts, which `site.yml`
gathers as the SSH user.

## Behavior

The role installs the packages with pacman too, so `--tags 3dprint` works on
its own. A package installed that way is not owned by the `packages` role,
which then never removes it.

Nautilus runs thumbnailers in a bwrap sandbox, where F3D's default backend
cannot open a display and the preview is marked failed. The role writes
`/etc/f3d/thumbnail.json` (root, `0644`, in a `0755` directory) to force the
headless EGL backend for every user. F3D reads `/etc/f3d` first, so a
`~/.config/f3d/thumbnail.json` can still override it.

GNOME never retries a file listed under `~/.cache/thumbnails/fail`. When the
F3D file changes, a handler removes the cache directories as the SSH user, and
Nautilus recreates them as it draws new previews. An unchanged run leaves the
cache alone.

## Tags

`3dprint` runs the role. A role name cannot start with a digit, so the tag
differs from the role name. See [Running](../../README.md#running) for the
commands.

## Dependencies

None. In `site.yml` the role runs last, after `obs`.

## Example Playbook

```yaml
- name: Configure the Linux workstations
  hosts: all
  become: true
  roles:
    - role: print3d
      when:
        - packages_action | default('install') != 'plan'
        - ansible_facts["os_family"] == "Archlinux"
        - "'24_3dprint' in (packages_selected_groups | default([]))"
      tags: [3dprint]
```

## License

Unlicense

## Author Information

pad
