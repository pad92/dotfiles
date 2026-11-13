# packages

Selects the package groups of a host, installs their packages, and, on
request, removes the managed packages that no selected group lists any more.
AUR packages are built with `yay`.

## Requirements

- Arch Linux or CachyOS, Debian or Ubuntu, or Fedora.
- Privilege escalation (`become: true`). AUR builds run as the regular user.
- On Arch Linux, the `package_manager` role first, so `multilib` is enabled.

## Role Variables

| Variable                            | Default                                                  | Description                                                                                                  |
| :---------------------------------- | :------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------- |
| `packages_host_groups`              | `null`                                                   | Groups of this host, set in `host_vars`. A list replaces the OS and GPU defaults; `null` keeps them.         |
| `packages_group_selection`          | undefined                                                | One-run override of the selection. Never extended by detection.                                              |
| `packages_action`                   | `install`                                                | `plan` (read-only), `install`, or `reconcile` (install, then remove what the role owns and no longer lists). |
| `packages_upgrade_system`           | `false`                                                  | Use `pacman -Syu` whenever packages are installed.                                                           |
| `packages_aur_action`               | `install`                                                | `install`, `ask` (confirm each AUR build) or `skip`.                                                         |
| `packages_aur_helper_preference`    | `[yay]`                                                  | AUR helpers, in order of preference.                                                                         |
| `packages_protected`                | `[]`                                                     | Extra packages that removals never touch.                                                                    |
| `packages_state_directory`          | `$XDG_STATE_HOME/dotfiles`                               | Where the saved selection and the owned packages are recorded.                                               |
| `packages_state_merge_selection`    | `false`                                                  | Add the selection to the saved one instead of replacing it (partial profiles such as `obs.yml`).             |
| `packages_razer_detection`          | `true`                                                   | Add `packages_razer_group` when a Razer USB device is connected.                                             |
| `packages_razer_required_group`     | `21_steam`                                               | Group that the selection must hold for the Razer detection to run.                                           |
| `packages_razer_group`              | `25_razer`                                               | Group added by the Razer detection.                                                                          |
| `packages_razer_usb_vendor_id`      | `'1532'`                                                 | Razer's USB vendor ID. Keep it quoted: an integer disables the detection.                                    |
| `packages_usb_sysfs_devices`        | `/sys/bus/usb/devices`                                   | Where the USB devices are read.                                                                              |
| `packages_gaming_required_packages` | `ananicy-cpp`, `power-profiles-daemon`, `python-gobject` | Packages the `gaming` role checks before configuring services.                                               |

The group lists live in `vars/`: the OS-family file (`archlinux.yml`,
`debian.yml`, `redhat.yml`), then the first matching exact-version,
major-version or distribution override (`cachyos.yml`, `debian-13.yml`,
`ubuntu-24.yml`). Selection, installation and reconciliation stay in separate
task files.

## Group selection

`tasks/selection.yml` only reads the host. The playbooks include it first with
the `always` tag, so every role that reads `packages_selected_groups` has it,
whatever tags are passed.

Groups come from the OS defaults and the detected GPUs. A host with its own
`packages_host_groups` replaces those defaults; the list must be a list, any
other type stops the play. `packages_group_selection` overrides both for one
run:

```sh
make deploy BECOME_PASS=1 ANSIBLE_ARGS="-e '{\"packages_group_selection\":[\"01_base\",\"03_gtk\"]}'"
```

### Gaming packages

`21_steam` selects Steam, Gamescope, MangoHud, `ananicy-cpp`,
`power-profiles-daemon` and `python-gobject` on Arch Linux and CachyOS. On
CachyOS it also selects Proton CachyOS SLR, `cachyos-ananicy-rules` and
`cachyos-settings`, which provides `game-performance`. These packages are added
only when the facts identify CachyOS, and they must come from the configured
CachyOS repositories: the role never builds them from the AUR.
`cachyos-settings` also installs CachyOS system defaults for sysctl, udev and
other components
([package documentation](https://wiki.cachyos.org/fr/features/cachyos_settings/)).

GameMode is excluded from the package lists. An already installed copy can be
removed by a reconcile only if the role owns it.

### Razer devices

A Razer mouse or keyboard needs OpenRazer for `razer_dpi.py`. When the
selection holds `21_steam`, the role reads the `idVendor` of each USB device and
adds `25_razer` if one reports Razer's vendor ID. The group installs
`openrazer-daemon`, `openrazer-driver-dkms` and `python-openrazer`; the DKMS
driver brings the headers of the running kernel with it.

The device has to be plugged in for the first run. Once the saved state
records `25_razer`, the group stays selected while the device is unplugged or
unreadable, so a later reconcile keeps OpenRazer. To remove it, set
`packages_razer_detection: false` in the host's `host_vars` and reconcile. To
install it with no device plugged in, list `25_razer` in
`packages_host_groups`. An explicit `packages_group_selection` is never
extended.

`dotfiles_openrazer_group` and `package_services_user_groups_by_group` repeat
the group name; a test checks that they agree.

## Installation

Installation is additive. On Arch Linux a package counts as installed when an
installed package provides its name (`pacman -T`), for example `foo-git` for
`foo`. Installing does not upgrade the whole system unless `multilib` was just
enabled or `packages_upgrade_system` is `true`.

If `yay` is missing, the role clones its AUR recipe, builds it as the current
user, then installs it with privilege escalation. makepkg keeps its package,
source, build and log destinations inside that temporary build tree. AUR
installation goes through the `dotfiles_aur` module, without pacman's
unsupported `--print-format` calls.

## Reconciliation

`packages_action=reconcile` removes the packages the role installed and that
no selected group lists any more. Removals never touch the built-in base set
(`base`, `glibc`, `pacman`, `systemd`, `linux` and `linux-*`, and a few
others) or `packages_protected`. Run `--check` to preview the changes.

## Tags

| Tag                  | Runs                                                         |
| :------------------- | :----------------------------------------------------------- |
| `packages`           | The whole role.                                              |
| `packages_install`   | Plan and install.                                            |
| `packages_reconcile` | Plan, install and reconcile.                                 |
| `yay`                | The AUR flow only, without the official repository packages. |

## Dependencies

None. On Arch Linux, run `package_manager` before it.

## Example Playbook

```yaml
- hosts: all
  become: true
  pre_tasks:
    - name: Select the package groups of this host
      ansible.builtin.include_role:
        name: packages
        tasks_from: selection
        apply:
          tags: [always]
      tags: [always]
  roles:
    - role: packages
      tags: [packages]
```

## License

Unlicense

## Author Information

pad
