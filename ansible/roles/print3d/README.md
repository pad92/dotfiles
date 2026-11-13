# print3d

Installs PrusaSlicer and F3D, and makes F3D's thumbnailers work in Nautilus so
3D files (STL, STEP, 3MF, glTF...) get a preview.

## Requirements

- Arch Linux, with `24_3dprint` selected. `site.yml` runs the role only then.
- Privilege escalation (`become: true`).

## Role Variables

| Variable                          | Default                                          | Description                                          |
| :-------------------------------- | :----------------------------------------------- | :--------------------------------------------------- |
| `print3d_packages`                | the `24_3dprint` group of the `packages` role    | Packages installed with pacman.                      |
| `print3d_f3d_config_dir`          | `/etc/f3d`                                       | System F3D configuration directory.                  |
| `print3d_f3d_config_owner`        | `root`                                           | Owner of the configuration.                          |
| `print3d_f3d_config_group`        | `root`                                           | Group of the configuration.                          |
| `print3d_f3d_thumbnail_options`   | `{rendering-backend: egl}`                       | Written to `thumbnail.json`.                         |
| `print3d_thumbnail_cache_dir`     | `$XDG_CACHE_HOME/thumbnails`                     | GNOME thumbnail cache of the SSH user.               |
| `print3d_thumbnail_cache_subdirs` | `fail`, `normal`, `large`, `x-large`, `xx-large` | Cache directories cleared when the F3D file changes. |

## Behavior

The role installs the packages with pacman too, so `TAGS=3dprint` works on its
own. A package installed that way is not owned by the `packages` role, which
then never removes it.

Nautilus runs thumbnailers in a bwrap sandbox, where F3D's default backend
cannot open a display and the preview is marked failed. The role writes
`/etc/f3d/thumbnail.json` (root, `0644`, in a `0755` directory) to force the
headless EGL backend for every user. F3D reads `/etc/f3d` first, so a
`~/.config/f3d/thumbnail.json` can still override it.

GNOME never retries a file listed under `~/.cache/thumbnails/fail`. When the
F3D file changes, a handler removes the cache directories; Nautilus recreates
them as it draws new previews. An unchanged run leaves the cache alone.

```sh
make deploy TAGS=3dprint BECOME_PASS=1
```

## Dependencies

None. `print3d_packages` reads the package lists of the `packages` role.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: print3d
      when: "'24_3dprint' in packages_selected_groups"
      tags: [3dprint]
```

## License

Unlicense

## Author Information

pad
