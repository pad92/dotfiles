# My Dotfiles

Linux desktop configuration for Arch Linux and CachyOS, built around Hyprland,
Zsh, Neovim, Alacritty, tmux, Waybar, and Mako.

![Hyprland desktop with Neovim, Waybar and Fastfetch on CachyOS](./dist/hyprland.webp)

[Changelog](./CHANGELOG.md) · [Releases](https://gitlab.com/pad92/dotfiles/-/releases) · [Arch installation guide](./dist/arch/install.md)

## Install

```sh
git clone https://gitlab.com/pad92/dotfiles.git ~/.dotfiles
cd ~/.dotfiles
./install
```

Install `ansible-playbook` first. Run `./install` from a regular user account
with `sudo` access. The playbook supports Arch Linux and CachyOS, Debian and
Ubuntu, and Fedora. It installs selected package groups and deploys dotfiles.
Use `./install --check` to preview package changes. Add `--tags dotfiles` to
preview dotfile changes without running package tasks.

Package groups are selected from OS defaults and detected GPU hardware. Set
`packages_host_groups` in `ansible/host_vars/localhost.yml` to choose groups by
hostname, or use `-e packages_group_selection=...` for a one-time override.
GPU groups are added only when all controllers can be classified. Package
mappings are in `ansible/roles/packages/vars/`.

On Arch, the installer configures color output, disk-space checks, five parallel
downloads, and the standard `multilib` repository in `/etc/pacman.conf`. Enabling
`multilib` triggers `pacman -Syu`. Otherwise, selected official packages are
installed without a full upgrade by default; use
`-e packages_upgrade_system=true` to request one.

Missing AUR packages are built with `yay`. If needed, the playbook installs its
build dependencies, builds it as the regular user, then installs it with
privilege escalation. Set `packages_aur_action=ask` to confirm AUR work or
`packages_aur_action=skip` to skip it.

Package installation is additive. Reconciliation removes only packages
recorded as managed by this installer, after a transaction preview and explicit
confirmation. Use `./install -e packages_action=reconcile` to review and apply
reconciliation. Packages installed before the state file was created remain
unmanaged.

The installer configures makepkg for native CPU builds on Arch Linux and
CachyOS and disables separate debug packages. Packages built with native CPU
flags may not run on computers with a different CPU.

## Ansible tags

Pass tags with `./install --tags <tag>`. The supported-distribution check always
runs. Tags on an enclosing role or task group include its subtasks.

| Tag                         | Description                                                                                                               |
| :-------------------------- | :------------------------------------------------------------------------------------------------------------------------ |
| `packages`                  | Run the package role.                                                                                                     |
| `packages_select`           | Select package groups.                                                                                                    |
| `packages_install`          | Configure Arch repositories and install selected packages.                                                                |
| `packages_reconcile`        | Configure repositories, install selected packages, and reconcile managed packages.                                        |
| `pacman`, `pacman_config`   | Configure `/etc/pacman.conf`; aliases.                                                                                    |
| `yay`                       | Select packages and run the AUR flow. Also runs `pacman` configuration, but skips selected official package installation. |
| `system`                    | Run system configuration.                                                                                                 |
| `ssh_client_hardening`      | Hash host names when the system SSH client adds new known-hosts entries.                                                        |
| `kernel_hardening`          | Apply desktop-compatible kernel protections through sysctl.                                                                  |
| `gpu_modules`               | Select package groups and configure NVIDIA/i915 kernel module settings.                                                   |
| `makepkg`, `makepkg_config` | Configure makepkg; aliases.                                                                                               |
| `dotfiles`                  | Run the full dotfiles role.                                                                                               |
| `dotfiles_submodules`       | Initialize Git submodules.                                                                                                |
| `dotfiles_deploy`           | Deploy dotfiles and user systemd units.                                                                                   |
| `dotfiles_runtime`          | Check Vim and update its plugins only when `dotfiles_update_vim_plugins=true`.                                            |
| `vim`                       | Update Vim plugins when `dotfiles_update_vim_plugins=true`.                                                               |
| `systemd`                   | Install user units, reload the manager when needed, and enable/start the graphical units listed in Ansible defaults.      |
| `hyprlock_carousel`         | Render the Hyprlock carousel helper.                                                                                      |

Mako and Waybar reload handlers run automatically when notified by changed
configuration. Their internal `mako_reload` and `waybar_reload` handler tags
are not standalone `--tags` options.

For example, `./install --tags yay --ask-become-pass` runs the AUR flow, and
`./install --tags dotfiles_deploy` deploys dotfiles without installing packages.
The installer forwards other arguments to `ansible-playbook`, including
`--check`, `--ask-become-pass`, and `-e`.

## Customize

Set Git identity in the untracked `~/.gitconfig.local`; the managed [`.gitconfig`](./ansible/roles/dotfiles/files/home/.gitconfig)
includes it.

| Configuration      | Location                                                                                                                               |
| :----------------- | :------------------------------------------------------------------------------------------------------------------------------------- |
| Shell and login    | [Zsh files](./ansible/roles/dotfiles/files/home/zsh/) and [`.zshrc`](./ansible/roles/dotfiles/templates/home/.zshrc.j2)                |
| Hyprland           | [`.config/hypr/`](./ansible/roles/dotfiles/files/home/.config/hypr/)                                                                   |
| Waybar             | [`.config/waybar/`](./ansible/roles/dotfiles/files/home/.config/waybar/)                                                               |
| Terminal and tmux  | [Alacritty](./ansible/roles/dotfiles/files/home/.config/alacritty/) and [`.tmux.conf`](./ansible/roles/dotfiles/files/home/.tmux.conf) |
| Editors            | [Neovim](./ansible/roles/dotfiles/files/home/.config/nvim/) and [Vim](./ansible/roles/dotfiles/files/home/.vimrc)                      |
| Wallpaper settings | [AWWW configuration sample](./ansible/roles/dotfiles/files/home/.config/awww/awww.conf-sample)                                         |

Host-aware files are rendered from `ansible/roles/dotfiles/templates/`. Static
files are copied from `ansible/roles/dotfiles/files/`. Conflicting regular files
are backed up with a `.bak` suffix; managed symbolic links are removed while
their targets are left untouched.

Use `make ansible-backup-ls` to list backups created for Ansible-managed
dotfiles, or `make ansible-backup-rm` to review and remove them after a
confirmation prompt. Both targets use `$HOME` by default; set
`ANSIBLE_BACKUP_ROOT=/path` on the `make` command line to select another root.

## Shell and editors

Zsh uses Oh My Zsh, autosuggestions, syntax highlighting, and custom aliases and
functions in [`zsh/`](./ansible/roles/dotfiles/files/home/zsh/). Notable helpers
include `arch_update`, `clean_arch`, `extract`, `mtail`, and GPG encrypt/decrypt
functions. The Neovim setup uses Lua, lazy.nvim, Telescope, Treesitter, Mason,
and native LSP; it requires Neovim 0.12+. The Vim setup uses Vundle.

The `mtail` function follows current and future log files across rotation. Quote
globs to include files created later:

```zsh
mtail '*.log' '/var/log/app/*.log'
```

## Desktop

The Hyprland configuration uses Lua and requires Hyprland 0.55+. See the
[session guide](./dist/arch/install.md#gnome-keyring-pam-setup) for TTY startup,
GNOME Keyring PAM, UWSM, and systemd session setup.

| Shortcut                            | Action                                           |
| :---------------------------------- | :----------------------------------------------- |
| `SUPER + Return`                    | Terminal                                         |
| `SUPER + E / C / W / M`             | File manager / editor / browser / music player   |
| `SUPER + [0-9]`                     | Switch workspace; add `Shift` to move the window |
| `SUPER + Arrows` or Vim keys        | Change focus; add `Shift` to move the window     |
| `SUPER + F` / `SUPER + ALT + Space` | Fullscreen / floating                            |
| `SUPER + L` / `SUPER + Delete`      | Lock / logout menu                               |
| `Print` / `SUPER + P`               | Screenshot                                       |

`awww.sh` selects wallpapers per monitor from local files or configured NFS/CIFS
mounts. Copy its sample to `~/.config/awww/awww.conf` to configure sources.
Renders are cached under a managed directory with a 2 GiB default quota;
references are preserved. ImageMagick is required. `awww.service` starts with
Hyprland and `awww_random.timer` changes wallpapers every 30 minutes.

Hyprlock displays time, battery, and media information. Its carousel option
uses configured AWWW sources. See the [Hyprlock templates and helpers](./ansible/roles/dotfiles/templates/home/.config/hypr/hyprlock.conf.j2)
for details. The LACT profile is deployed to `~/.config/lact/config.yaml`, not
`/etc/lact/config.yaml`. Verify the GPU identifier and review the fan curves
before relying on it.

## Scripts

The playbook deploys [`~/.bin/`](./ansible/roles/dotfiles/files/home/.bin/) and
adds it to `PATH` in Zsh.

| Script                                                                                                                           | Purpose                                          |
| :------------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------- |
| [`steam-optimize`](./ansible/roles/dotfiles/files/home/.bin/steam-optimize)                                                      | Configure per-game Vulkan and Gamescope options. |
| [`backup.sh`](./ansible/roles/dotfiles/files/home/.bin/backup.sh)                                                                | Back up files with rsync over SSH.               |
| [`awww.sh`](./ansible/roles/dotfiles/files/home/.bin/awww.sh)                                                                    | Select and render wallpapers.                    |
| [`razer_dpi.py`](./ansible/roles/dotfiles/files/home/.bin/razer_dpi.py)                                                          | Configure Razer mouse DPI.                       |
| [`hypr-screenshot.sh`](./ansible/roles/dotfiles/files/home/.bin/hypr-screenshot.sh)                                              | Capture the desktop showcase.                    |
| [`comcut`](./ansible/roles/dotfiles/files/home/.bin/comcut), [`comskip.sh`](./ansible/roles/dotfiles/files/home/.bin/comskip.sh) | Detect and remove commercial breaks.             |
| [`diff-cmd`](./ansible/roles/dotfiles/files/home/.bin/diff-cmd)                                                                  | Compare command output for two arguments.        |
| [`vscodium_ext.sh`](./ansible/roles/dotfiles/files/home/.bin/vscodium_ext.sh)                                                    | Install VSCodium extensions.                     |

Package cleanup is opt-in. Pass `--clean-packages` to `backup.sh` to run
`yay -Sc` on Arch or `apt autoremove --purge` on Debian.

To install the Vim configuration, run [`scripts/vim.sh`](./scripts/vim.sh).
GitLab CI also builds downloadable [Vim](https://gitlab.com/pad92/dotfiles/-/jobs/artifacts/main/download?job=package_vim)
and [Neovim](https://gitlab.com/pad92/dotfiles/-/jobs/artifacts/main/download?job=package_nvim)
configuration archives.

## CI and releases

GitHub, GitLab, and Gitea use shared scripts in [`scripts/ci/`](./scripts/ci/).
See the [GitHub workflow documentation](./.github/workflows/README.md) and
[GitLab CI documentation](./.gitlab/README.md). Tags matching `v*` publish a
release using the matching changelog section.

_Maintained by [pad](https://gitlab.com/pad92)🐐 since 2015._
