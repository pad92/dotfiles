# packages

Selects the package groups of a host, installs their packages, and on request
removes the managed packages that no selected group lists any more. AUR
packages are built with `yay`.

## Requirements

- Arch Linux or CachyOS, Debian or Ubuntu, or Fedora.
- Privilege escalation (`become: true`). AUR builds run as the SSH user.
- On Arch Linux, the `package_manager` role first, so `multilib` is enabled.

## Role Variables

| Variable                            | Default                                                                                                    | Description                                                                                                  |
| :---------------------------------- | :--------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------- |
| `packages_host_groups`              | `null`                                                                                                     | Groups of this host, set in `host_vars`. A list replaces the OS and GPU defaults. `null` keeps them.         |
| `packages_state_directory`          | `{{ ansible_facts['env'].get('XDG_STATE_HOME') or ansible_facts['user_dir'] ~ '/.local/state' }}/dotfiles` | Where the saved selection and the owned packages are recorded, in the SSH user's home.                       |
| `packages_action`                   | `install`                                                                                                  | `plan` (read-only), `install`, or `reconcile` (install, then remove what the role owns and no longer lists). |
| `packages_state_merge_selection`    | `false`                                                                                                    | Add the selection to the saved one instead of replacing it, for partial runs such as `--tags obs`.           |
| `packages_upgrade_system`           | `false`                                                                                                    | On Arch Linux, run `pacman -Syu` before installing missing official packages.                                |
| `packages_aur_action`               | `install`                                                                                                  | `install`, `ask` or `skip`. See [AUR packages](#aur-packages).                                               |
| `packages_aur_helper_preference`    | `[yay]`                                                                                                    | AUR helpers, in order of preference.                                                                         |
| `packages_razer_detection`          | `true`                                                                                                     | Add `packages_razer_group` when a Razer USB device is connected.                                             |
| `packages_razer_required_group`     | `21_steam`                                                                                                 | Group that the selection must hold for the Razer detection to run.                                           |
| `packages_razer_group`              | `25_razer`                                                                                                 | Group added by the Razer detection.                                                                          |
| `packages_razer_usb_vendor_id`      | `'1532'`                                                                                                   | Razer's USB vendor ID. Keep it quoted: an integer disables the detection.                                    |
| `packages_usb_sysfs_devices`        | `/sys/bus/usb/devices`                                                                                     | Where the USB devices are read.                                                                              |
| `packages_gaming_required_packages` | `[ananicy-cpp, power-profiles-daemon, python-gobject]`                                                     | Packages the `gaming` role checks before configuring services. `vars/cachyos.yml` adds two more.             |
| `packages_protected`                | `[]`                                                                                                       | Extra packages that removals never touch.                                                                    |

External variable:

- `packages_group_selection`: one-run override of the whole selection, passed
  with `-e`. Detection never extends it.

The group lists live in `vars/`: the OS-family file (`archlinux.yml`,
`debian.yml`, `redhat.yml`), then the first matching exact-version,
major-version or distribution override (`cachyos.yml`, `debian-13.yml`,
`ubuntu-24.yml`).

## Group selection

`tasks/selection.yml` only reads the host. `site.yml` includes it in its
`pre_tasks` with the `always` tag (see [Pre-tasks](../../PLAYBOOKS.md#pre-tasks)),
so every role that reads `packages_selected_groups` has it whatever tags are
passed. The role includes it itself when it runs alone.

Groups come from the OS defaults and the detected GPUs. GPUs are read with
`lspci -Dnn`, with a sysfs fallback. A display controller the role cannot
classify fails the run unless `packages_group_selection` is set. A host with
its own `packages_host_groups` replaces the defaults. The value must be a list,
and any other type stops the play. `packages_group_selection` overrides both
for one run:

```sh
make deploy BECOME_PASS=1 ANSIBLE_ARGS="-e '{\"packages_group_selection\":[\"01_base\",\"03_gtk\"]}'"
```

When a selected group installs a DKMS driver, the role adds the headers package
that matches the running kernel. It finds it by asking pacman which package
owns `/usr/lib/modules/<kernel>/vmlinuz`.

### Gaming packages

On Arch Linux and CachyOS, `21_steam` selects Steam, Gamescope, MangoHud,
Discord, Ludusavi, `ananicy-cpp`, `power-profiles-daemon`, `python-gobject` and
`python-vdf` (for the `steam-optimize --install` configurator). On CachyOS it
also selects Proton CachyOS SLR, `cachyos-ananicy-rules` and
`cachyos-settings`, which provides `game-performance`. These packages are added
only when the facts identify CachyOS. The role checks that the configured
CachyOS repositories provide them and fails otherwise, since it never builds
them from the AUR. `cachyos-settings` also installs CachyOS system defaults for
sysctl, udev and other components
([package documentation](https://wiki.cachyos.org/fr/features/cachyos_settings/)).

A selected package that needs `multilib` fails the run when the repository is
not enabled.

GameMode is excluded from the package lists. An already installed copy is
removed by a reconcile only if the role owns it.

### Razer devices

A Razer mouse or keyboard needs OpenRazer for `razer_dpi.py`. When the
selection holds `21_steam`, the role reads the `idVendor` of each USB device and
adds `25_razer` if one reports Razer's vendor ID. The group installs
`openrazer-daemon`, `openrazer-driver-dkms`, `python-openrazer` and `razer-cli`
(AUR), which `steam-optimize --dpi` uses to set and restore the mouse DPI of a
game. Without it, `--dpi` is ignored and the game launches with the DPI
unchanged.

The device has to be plugged in for the first run. Once the saved state
records `25_razer`, the group stays selected while the device is unplugged or
unreadable, so a later reconcile keeps OpenRazer. To remove it, set
`packages_razer_detection: false` in the host's `host_vars` and reconcile. To
install it with no device plugged in, list `25_razer` in
`packages_host_groups`. An explicit `packages_group_selection` is never
extended.

`dotfiles_openrazer_group` and `package_services_user_groups_by_group` repeat
the group name, and a test checks that they agree.

## Installation

Installation is additive. On Arch Linux a package counts as installed when an
installed package provides its name (`pacman -T`), for example `foo-git` for
`foo`. Installing does not upgrade the whole system unless `multilib` was just
enabled by `package_manager`, or `packages_upgrade_system` is `true` and some
official packages are missing.

Check mode cannot simulate installations. In check mode the role prints the
plan and leaves the packages alone, and the other roles still run.

### AUR packages

If `yay` is missing, the role clones its AUR recipe, builds it as the SSH user,
then installs it with privilege escalation. makepkg keeps its package, source,
build and log destinations inside that temporary build tree. AUR installation
goes through the `dotfiles_aur` module, which avoids pacman's `--print-format`
calls that AUR helpers do not support.

With `packages_aur_action: ask` the role asks at most twice: once before
building `yay` (`[Y/n]`), and once for the whole list of AUR packages
(`[y/N]`). `skip` leaves every AUR package out.

## Reconciliation

`packages_action=reconcile` removes the packages the role installed and that no
selected group lists any more. It runs only when the saved state is valid and
every desired package is installed. Removals never touch the built-in base set
(`base`, `glibc`, `pacman`, `systemd`, `linux` and `linux-*`, and a few
others) or `packages_protected`.

On Arch Linux the role first previews the transaction with
`pacman -Rs --print`, then asks you to type `REMOVE` to remove the packages
with their unneeded dependencies, `KEEP` to leave them installed and stop
managing them, or anything else to cancel. Debian and Fedora accept `REMOVE`
only.

`make plan` lists the removal candidates without changing anything. The saved
state file has mode `0600` inside a `0700` directory.

## Tags

| Tag        | Runs                                                                 |
| :--------- | :------------------------------------------------------------------- |
| `packages` | The whole role.                                                      |
| `obs`      | The whole role, from `site.yml`, for the OBS profile.                |
| `yay`      | The AUR flow and the plan, without the official repository packages. |
| `always`   | The group selection, which every run needs.                          |

## Dependencies

None. In `site.yml`, `package_manager` runs before it.

## Example Playbook

The selection include is shown in [Pre-tasks](../../PLAYBOOKS.md#pre-tasks).
Used alone, the role runs it itself.

```yaml
- hosts: all
  become: true
  roles:
    - role: packages
      tags: [packages, obs]
```

## License

Unlicense

## Author Information

pad
