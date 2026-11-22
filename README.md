# My Dotfiles

[![Pipeline](https://gitlab.com/pad92/dotfiles/badges/main/pipeline.svg)](https://gitlab.com/pad92/dotfiles/-/pipelines)
[![Latest release](https://gitlab.com/pad92/dotfiles/-/badges/release.svg)](https://gitlab.com/pad92/dotfiles/-/releases)

A Hyprland desktop for Arch Linux and CachyOS, with Zsh, Neovim, Alacritty,
tmux, Waybar, and Mako, set up by a single Ansible playbook.

[![Hyprland demo: Neovim and Fastfetch windows open on an empty desktop and move, then a Hyprlauncher search, a Mako notification, the logout menu, and the Hyprlock screen](./dist/hyprland-demo.webp)](./dist/hyprland.webp)

Neovim and a Fastfetch terminal opening on an empty desktop, the terminal
moving across and back, a Hyprlauncher search, a Mako notification, the
logout menu, then Hyprlock, recorded by `make screenshot` from the Hyprland
config in this repository. Click it for the full-size still.

[Changelog](./CHANGELOG.md) · [Releases](https://gitlab.com/pad92/dotfiles/-/releases) ·
[Arch installation guide](./dist/arch/install.md) · [Ansible guide](./ansible/README.md)

## Highlights

- Hyprland 0.55+ configured in Lua, with Waybar, Hyprlauncher, Hyprlock, and
  per-monitor wallpapers.
- Mako notifications in the top-right corner, silenced while `steam-optimize`
  runs a game, except for critical alerts.
- Zsh with Oh My Zsh, Neovim 0.7.2+ with native LSP, Vim, Alacritty, and tmux.
- Standalone Neovim, Vim and Zsh packages, installed with one `curl` or `wget`
  command and no Ansible: see [Editor packages](#editor-packages).
- A Gruvbox Dark palette shared by Hyprland, Waybar, Mako, Hyprlock, tmux,
  Neovim, and Vim.
- One Ansible playbook for packages, system settings, and dotfiles on Arch
  Linux/CachyOS, Debian/Ubuntu, and Fedora.
- Gaming and GPU tuning: `ananicy-cpp`, `power-profiles-daemon`, AMD CPU
  settings, and LACT profiles for AMD and NVIDIA.

## Quick start

You need Git, `make`, a regular user with `sudo` access, and Ansible with the
collections in [`ansible/requirements.yml`](./ansible/requirements.yml). The
full `ansible` package ships them; with `ansible-core` alone, install them
into the repository after cloning.

```sh
git clone https://gitlab.com/pad92/dotfiles.git ~/.dotfiles
cd ~/.dotfiles
# Only with ansible-core:
make galaxy
make check   # preview
make deploy
```

`make deploy` installs packages and deploys the configuration to your home
directory. Installation is additive: packages that were already installed stay
unmanaged.

Ansible reaches the machine over SSH, even when it is the one you type on.
`HOST` selects a host of `ansible/inventory.yml` and defaults to the short
hostname (`uname -n` up to the first dot).
The target needs an SSH server; the repository only has to be cloned on the
machine you run `make` from, and that clone can be deleted once deployed:
`make deploy HOST=PadsP5560` configures the laptop from the desktop. A new
machine first gets an inventory entry; see
[Per-host settings](./ansible/README.md#per-host-settings).

## Editor packages

The Neovim, Vim and Zsh configurations are published as standalone archives,
built by the GitLab pipeline. They need neither Ansible nor a clone of this
repository, only `curl` (or `wget`) and `tar`.

Back up your current configuration first: extraction replaces files with the
same names. Without `curl`, use `wget -qO-` in place of `curl -fsSL`. To list
an archive instead of extracting it, replace `tar -xz -C ~` with `tar -tz`.

### Neovim

Installs `~/.config/nvim`.

```sh
curl -fsSL 'https://gitlab.com/pad92/dotfiles/-/jobs/artifacts/main/raw/nvim.tar.gz?job=package_nvim' | tar -xz -C ~
```

### Vim

Installs `~/.vim` and `~/.vimrc`, with the plugins at the pinned commits. The
script refuses to run when either already exists.

```sh
curl -fsSL https://gitlab.com/pad92/dotfiles/-/raw/main/scripts/vim.sh | bash
```

### Zsh

Installs `~/.zshenv`, `~/.zshrc` and `~/.local/share/dotfiles/zsh`, with the
plugins at the pinned commits and a `.zshrc` rendered for any home directory.
`~/.zprofile`, which starts the Hyprland session from a login shell, is left
out.

```sh
curl -fsSL 'https://gitlab.com/pad92/dotfiles/-/jobs/artifacts/main/raw/zsh.tar.gz?job=package_zsh' | tar -xz -C ~
```

## Common tasks

`make help` lists the targets and their variables. `deploy`, `check`, `plan`,
`tags` and `tasks` share these variables, except that `plan` refuses `TAGS` and
`SKIP_TAGS`: a selection could skip the stop after the package plan and let
the next roles change the host.

| Variable       | Effect                                                      |
| :------------- | :---------------------------------------------------------- |
| `PLAYBOOK`     | Only `site` exists; `TAGS=obs` runs its OBS profile.        |
| `HOST`         | Inventory host or pattern; defaults to this machine.        |
| `TAGS`         | Run only these comma-separated tags (`--tags`).             |
| `SKIP_TAGS`    | Skip these comma-separated tags (`--skip-tags`).            |
| `BECOME_PASS`  | Any value asks for the sudo password (`--ask-become-pass`). |
| `ANSIBLE_ARGS` | Any other option, passed last to `ansible-playbook`.        |

| Goal                                 | Command                                                      |
| :----------------------------------- | :----------------------------------------------------------- |
| Preview a full run                   | `make check`                                                 |
| Print only the package plan          | `make plan`                                                  |
| List the tags, or the tasks they run | `make tags` / `make tasks TAGS=dotfiles`                     |
| Deploy the dotfiles only             | `make deploy TAGS=dotfiles_deploy`                           |
| Preview the dotfiles only            | `make check TAGS=dotfiles`                                   |
| Remove packages this installer added | `make deploy ANSIBLE_ARGS="-e packages_action=reconcile"`    |
| Set up the Steam group               | `make deploy TAGS=packages,gaming BECOME_PASS=1`             |
| Install only OBS and its demo scenes | `make deploy TAGS=obs BECOME_PASS=1`                         |
| Upgrade the whole system on Arch     | `make deploy ANSIBLE_ARGS="-e packages_upgrade_system=true"` |
| Install the pinned collections       | `make galaxy`, or `make galaxy-force` to reinstall them      |
| Remove backups and leftovers         | `make clean`, or `make clean DRY_RUN=1` to list them only    |
| Build and open the documentation     | `make pages`                                                 |

`make install` still works as an alias of `make deploy`, and
`make install-obs` as an alias of `make deploy TAGS=obs`. Reconciliation previews the removals and asks for
confirmation.

`make clean` removes what deployments and earlier versions left behind: the
`.bak` backups of managed paths, broken links under deployed paths, files a
role no longer ships, retired submodule metadata, Python caches and `.desktop`
launchers whose program, Wine prefix or Steam game is gone. Ansible
backups of the managed files in `/etc` (`name.PID.DATE@TIME~`) are included;
they are root-owned, so `sudo make clean CLEAN_ROOT=$HOME` removes them and a
plain run only lists them. It lists
everything first and asks you to type `REMOVE` before deleting backups and
launchers; see
[Cleaning up](./ansible/README.md#cleaning-up). `make ansible-backup-ls` and
`make ansible-backup-rm` remain as aliases of `make clean DRY_RUN=1` and
`make clean`.

<details>
<summary>Package selection and Arch specifics</summary>

Package groups come from OS defaults and detected GPUs. Each machine sets its
own list, `packages_host_groups`, in `ansible/host_vars/<hostname>.yml`,
or you pass `-e packages_group_selection=...` for one run. Automatic GPU selection
requires every controller to be identified. Package variables load by OS
family, then use the first matching exact-version, major-version, or
distribution override.

On Arch, Ansible configures pacman, enables the standard `multilib` repository,
and runs `pacman -Syu` when it enables that repository. Missing AUR packages
use `yay`, which Ansible can build as the regular user. Set
`packages_aur_action=ask` to confirm AUR work or `skip` to leave it out. Native
makepkg builds disable debug packages and may not run on a different CPU.

</details>

## Ansible tags

Run a subset with `make deploy TAGS=<tag>`. The
supported-distribution check and the read-only package group selection always
run. The [Ansible guide](./ansible/README.md) lists the roles and covers
variables, package ownership, and system settings.

| Tags                                       | Action                                                                          |
| :----------------------------------------- | :------------------------------------------------------------------------------ |
| `package_manager`                          | Configure pacman and makepkg.                                                   |
| `packages`                                 | Configure pacman, then install and reconcile packages.                          |
| `pacman`                                   | Configure `/etc/pacman.conf`.                                                   |
| `yay`                                      | Configure pacman and run the AUR flow only.                                     |
| `system`                                   | Run every host role from `lact` to `gnome_keyring`, and makepkg.                |
| `package_services`                         | Enable the services and user groups of the selected package groups.             |
| `docker`                                   | Add the Docker group users.                                                     |
| `hardening`                                | Configure SSH client defaults and desktop sysctls.                              |
| `ssh_client_hardening`, `kernel_hardening` | Configure SSH client defaults or desktop sysctls.                               |
| `dns`                                      | Make systemd-resolved the only resolver, for the host and Docker.               |
| `vpn`                                      | Configure the openfortivpn SAML VPN.                                            |
| `gpu`                                      | Configure NVIDIA/i915 kernel modules and hybrid runtime PM.                     |
| `makepkg`                                  | Configure native Arch builds.                                                   |
| `cpu_power`                                | Apply supported AMD CPU settings.                                               |
| `time_sync`                                | Enable systemd-timesyncd when no other NTP client runs.                         |
| `power_save`                               | Set audio (and opt-in Wi-Fi) power-saving module options on a portable machine. |
| `iwlwifi`                                  | Write the Intel Wi-Fi module options a host lists.                              |
| `wireless_regdom`                          | Set the Wi-Fi regulatory domain (`wireless_regdom_country`).                    |
| `gnome_keyring`                            | Unlock the GNOME keyring at a TTY login through PAM.                            |
| `gaming`                                   | Check dependencies and configure services for the Steam group.                  |
| `lact`                                     | Manage `/etc/lact/config.yaml`.                                                 |
| `obs`, `obs_config`, `obs_virtualcam`      | Configure OBS for `22_obs`. On its own, `obs` installs OBS and nothing else.    |
| `3dprint`                                  | Install PrusaSlicer and F3D, and set up F3D previews of 3D files in Nautilus.   |
| `dotfiles`                                 | Run the `dotfiles`, `audio` and `agent_cli` roles.                              |
| `audio`                                    | Write the PipeWire and WirePlumber configuration: clean mic and voice effects.  |
| `dotfiles_deploy`                          | Run only the `dotfiles` role: configuration, pinned Vim and Zsh plugins.        |
| `agent_cli`                                | Set the Claude Code and Codex status lines and the Claude Code token savings.   |
| `dotfiles_claude`                          | Add the Claude Code status line when `claude` is installed.                     |
| `dotfiles_rtk`                             | Install RTK and merge its Claude Code hook (`agent_cli_rtk_enabled`).           |
| `dotfiles_codex`                           | Set the Codex status line when `codex` is installed.                            |
| `systemd`                                  | Deploy user units and enable the units in `dotfiles_systemd_graphical_units`.   |
| `hyprlock_carousel`                        | Render the lock-screen carousel helper.                                         |

Changed files notify their handlers: Mako and Waybar reload, active audio
services reload or restart (the SwayOSD server restarts with them), and active user units whose definitions changed
restart after `daemon-reload`. Hypridle needs `WAYLAND_DISPLAY` in the user
systemd environment to start.

## Desktop

The Hyprland configuration is written in Lua. See the
[session guide](./dist/arch/install.md#gnome-keyring-pam-setup) for TTY
startup, GNOME Keyring PAM, UWSM, and the systemd session.

| Shortcut                                            | Action                                                          |
| :-------------------------------------------------- | :-------------------------------------------------------------- |
| `SUPER + Return`                                    | Terminal                                                        |
| `SUPER + E / C / W`                                 | File manager / editor / browser                                 |
| `SUPER + D`                                         | Application menu                                                |
| `SUPER + F1`                                        | List the keybindings Hyprland has loaded                        |
| `SUPER + SHIFT + Return`                            | Password manager (Proton Pass)                                  |
| `SUPER + SHIFT + Q`                                 | Close the window                                                |
| `SUPER + F` / `SUPER + ALT + Space`                 | Fullscreen / floating                                           |
| `ALT + Tab`                                         | Cycle windows and raise the focused one                         |
| `SUPER + Arrows`                                    | Change focus; add `Shift` to move the window                    |
| `SUPER + [` / `SUPER + ]`                           | Focus the window on the left / right                            |
| `SUPER + Left click` / `Right click`                | Drag to move / resize the window                                |
| `SUPER + [0-9]`                                     | Switch workspace; add `Shift` to move the window there          |
| `SUPER + ALT + [0-9]`                               | Send the window to a workspace and stay (keypad too)            |
| `CTRL + SUPER + Left / Right`                       | Previous / next workspace                                       |
| `SUPER + L` / `SUPER + Delete`                      | Lock / logout menu                                              |
| `SUPER + SHIFT + V`                                 | Clipboard history                                               |
| `SUPER + ALT + Right`                               | Change wallpaper                                                |
| `SUPER + N`                                         | Dismiss notifications; `Shift` restores the last                |
| `Print` / `SUPER + P`                               | Screenshot of a region, then edit it in Swappy                  |
| `CTRL + Print` / `SUPER + CTRL + P`                 | Record a window (click) or a region (drag); press again to stop |
| `CTRL + SHIFT + Print` / `SUPER + CTRL + SHIFT + P` | Record the focused screen; press again to stop                  |
| `SUPER + Page Up / Page Down`                       | Zoom in / out around the pointer; `SUPER + Home` resets         |

Volume, media, brightness and screenshot keys also work on the lock screen.
Caps Lock shows its state in an on-screen indicator.

Mako shows up to five notifications in the top-right corner, newest first, and
draws them above fullscreen windows. `steam-optimize` turns on do-not-disturb
during games; critical alerts still appear and stay until dismissed.

`awww.sh` picks wallpapers per monitor from local files or NFS/CIFS mounts.
Copy its sample to `~/.config/awww/awww.conf` to configure sources. Renders are
cached with a 2 GiB default quota, and `awww_random.timer` changes wallpapers
every 30 minutes. ImageMagick is required.

Recordings are H.264 MP4 files at 30 fps, without sound, saved in
`~/Videos/Recordings` (the XDG videos folder). A few seconds of a 1440p screen
take a few hundred kilobytes. Frames are copied continuously, so a still screen
records correctly, and encoding a 1440p screen uses about 1.5 CPU cores while
it runs. The path is copied to the clipboard when the recording stops. While it
runs, Waybar shows a red `REC` label; clicking it stops the recording. A window
is recorded as the area it covered when you picked it: if you move it, it
leaves the frame, and anything drawn over it is recorded too.

Settings are environment variables of the Hyprland session (for example in
`~/.config/uwsm/env-hyprland`), documented at the top of
[`hypr-record.sh`](./ansible/roles/dotfiles/files/home/.bin/hypr-record.sh):
`HYPR_RECORD_AUDIO=1` adds the default audio input, and `HYPR_RECORD_HWENC=1`
with `HYPR_RECORD_VAAPI_DEVICE` encodes on the GPU, falling back to libx264 if
the encoder does not start.

Hyprlock shows the time, date, battery, and current media, with the
clock and the password field centered in the logout menu's style. Its carousel option uses
the `awww` sources; see the
[Hyprlock template](./ansible/roles/dotfiles/templates/home/.config/hypr/hyprlock.conf.j2).

## Gaming and GPUs

Select the `21_steam` group, then run
`make deploy TAGS=packages,gaming BECOME_PASS=1`. The
group installs `ananicy-cpp` and `power-profiles-daemon` instead of GameMode.
Ansible enables both services and stops if another known CPU power manager is
active or enabled. On CachyOS it also adds the CachyOS Ananicy rules, Proton,
and `cachyos-settings`, which provides `game-performance`. `steam-optimize`
works without `game-performance` and sets shader-cache limits for AMD and
NVIDIA.

The `cpu_power` tag sets the AMD P-State energy preference on supported
CPUs; see [AMD options](./ansible/roles/cpu_power/README.md).

The `lact` tag manages `/etc/lact/config.yaml` with the GPU identifiers
reported by the running LACT daemon. It keeps existing profiles and fan curves,
backs up changes, and restarts `lactd` when needed. It adds `Auto`, `Adaptive`,
and `PreferMaximumPerformance` profiles, named after LACT's PowerMizer modes,
for detected AMD and NVIDIA GPUs. Intel GPU settings are left unchanged.

See the [gaming setup](./ansible/roles/gaming/README.md) for overrides and
dependencies.

## Customize

Set your Git identity in the untracked `~/.gitconfig.local`; the managed
[`.gitconfig`](./ansible/roles/dotfiles/files/home/.gitconfig) includes it.

| Configuration      | Location                                                                                                                               |
| :----------------- | :------------------------------------------------------------------------------------------------------------------------------------- |
| Shell and login    | [Zsh files](./ansible/roles/dotfiles/files/home/zsh/) and [`.zshrc`](./ansible/roles/dotfiles/templates/home/.zshrc.j2)                |
| Hyprland           | [`.config/hypr/`](./ansible/roles/dotfiles/files/home/.config/hypr/)                                                                   |
| Waybar             | [`.config/waybar/`](./ansible/roles/dotfiles/files/home/.config/waybar/)                                                               |
| Notifications      | [`.config/mako/config`](./ansible/roles/dotfiles/templates/home/.config/mako/config.j2)                                                |
| Terminal and tmux  | [Alacritty](./ansible/roles/dotfiles/files/home/.config/alacritty/) and [`.tmux.conf`](./ansible/roles/dotfiles/files/home/.tmux.conf) |
| Editors            | [Neovim](./ansible/roles/dotfiles/files/home/.config/nvim/) and [Vim](./ansible/roles/dotfiles/files/home/.vimrc)                      |
| Wallpaper settings | [`awww` configuration sample](./ansible/roles/dotfiles/files/home/.config/awww/awww.conf-sample)                                       |

Static files are copied from `ansible/roles/dotfiles/files/` and host-aware
files are rendered from `ansible/roles/dotfiles/templates/`. Managed paths that
conflict are backed up before replacement. Unit symlinks stay links; deployment
stops if a regular file or directory occupies one of their destinations.

## Shell and editors

Zsh uses Oh My Zsh, autosuggestions, syntax highlighting, and the aliases and
functions in [`zsh/`](./ansible/roles/dotfiles/files/home/zsh/), including
`arch_update`, `clean_arch`, `extract`, `mtail`, and GPG helpers. `mtail`
follows log files across rotation; quote globs to include files created later:

```zsh
mtail '*.log' '/var/log/app/*.log'
```

Completion comes from zsh, the packages and the plugins, in that order.
Commands that only ship a bash completion are completed through
`bashcompinit` when their file works without the bash-completion helpers;
otherwise zsh completes file names. The caches live in `~/.zcache`: delete
`~/.zcache/bash-completions` or `~/.zcache/generated/` to rebuild them.

The completion dump is rebuilt when a directory of `fpath` changes, so a new
package is completed at the next shell start. `btop`, `gamescope`, `waybar`,
`hyprctl` and `lact`, which ship no completion, are completed from their
`--help`; add commands to `_dotfiles_generic_help_commands` in `~/.zshrc`
(only commands whose `--help` prints usage and exits). fzf's `**<TAB>`
completion is loaded; its key bindings are not.

Neovim uses Lua, Telescope, Treesitter, Mason, and native LSP. Neovim 0.8+
loads plugins with lazy.nvim; Neovim 0.7.2 uses a compatibility loader with
older plugin releases. Vim loads its plugins as a Vim package from
`~/.vim/pack/dotfiles/start/`, cloned at the commits the role pins.

Zed is installed on Arch with the `10_sre_devops` package group. In Zed,
`CTRL + ALT + V` saves the active file and runs
[`vault-toggle`](./ansible/roles/dotfiles/files/home/.bin/vault-toggle) on it:
a plain file is encrypted with Ansible Vault, an encrypted one is decrypted in
place. The playbook manages `~/.config/zed/tasks.json` and `keymap.json` for
this, so edits made to them in Zed are replaced (with a `.bak` copy) on the
next run. `settings.json` is left alone.

`vault-toggle` takes the password from `ANSIBLE_VAULT_PASSWORD_FILE` or
`ANSIBLE_VAULT_IDENTITY_LIST`, then from the project `ansible.cfg`, then from
the nearest `.vault`, `.vault_pass`, `.vault_pass.txt` or `.vault-password`
above the file, and prompts as a last resort. A password file found that way
is used only if you own it, it is not executable and no one else can write
to it, because ansible-vault runs an executable password file. Decryption is
refused when Git tracks the file or does not ignore it; `vault-toggle --force
FILE` overrides that from a terminal.

## Scripts

The playbook deploys [`~/.bin/`](./ansible/roles/dotfiles/files/home/.bin/) and
Zsh adds it to `PATH`.

| Script                                                                                                                           | Purpose                                          |
| :------------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------- |
| [`steam-optimize`](./ansible/roles/dotfiles/files/home/.bin/steam-optimize)                                                      | Configure per-game Vulkan and Gamescope options. |
| [`backup.sh`](./ansible/roles/dotfiles/files/home/.bin/backup.sh)                                                                | Back up files with rsync over SSH.               |
| [`awww.sh`](./ansible/roles/dotfiles/files/home/.bin/awww.sh)                                                                    | Select and render wallpapers.                    |
| [`razer_dpi.py`](./ansible/roles/dotfiles/files/home/.bin/razer_dpi.py)                                                          | Configure Razer mouse DPI.                       |
| [`hypr-screenshot.sh`](./ansible/roles/dotfiles/files/home/.bin/hypr-screenshot.sh)                                              | Record the desktop still and animated demo.      |
| [`hypr-record.sh`](./ansible/roles/dotfiles/files/home/.bin/hypr-record.sh)                                                      | Record a screen or a window as a light MP4.      |
| [`hypr-keybinds.sh`](./ansible/roles/dotfiles/files/home/.bin/hypr-keybinds.sh)                                                  | List the loaded keybindings (`SUPER + F1`).      |
| [`comcut`](./ansible/roles/dotfiles/files/home/.bin/comcut), [`comskip.sh`](./ansible/roles/dotfiles/files/home/.bin/comskip.sh) | Detect and remove commercial breaks.             |
| [`diff-cmd`](./ansible/roles/dotfiles/files/home/.bin/diff-cmd)                                                                  | Compare command output for two arguments.        |
| [`vscodium_ext.sh`](./ansible/roles/dotfiles/files/home/.bin/vscodium_ext.sh)                                                    | Install VSCodium extensions.                     |
| [`vault-toggle`](./ansible/roles/dotfiles/files/home/.bin/vault-toggle)                                                          | Encrypt or decrypt a file with Ansible Vault.    |

`backup.sh` copies `$HOME` and `/etc` to the NAS with rsync over SSH and saves
the installed-package list in `dist/<distribution>/`. Options, thresholds and
exit status are documented at the top of the script.

- `-v`, `--verbose` lists each transferred file.
- `--clean-packages` cleans the package cache (Arch) or removes unneeded
  packages (Debian) after a successful backup.
- `--max-deletions=N` and `--force-delete` bound or lift the deletion limit (rsync `--max-delete`).

## Development

| Command             | What it does                                                                |
| :------------------ | :-------------------------------------------------------------------------- |
| `make verify`       | Run `make lint`, then `make test`.                                          |
| `make test`         | Run the Python and shell test suites. Set `JOBS=N` to limit parallelism.    |
| `make coverage`     | Run the Python tests under coverage.py and enforce the `.coveragerc` floor. |
| `make lint-ansible` | Run ansible-lint, yamllint, and the playbook syntax check.                  |
| `make screenshot`   | Render the desktop showcase at the top of this page (`RES`, `SETTLE`, ...). |

The pre-push hook runs `make coverage` and the shell tests, as the CI does, so
a push that lowers the coverage below the `.coveragerc` floor is refused
locally. Commits stay fast: the suite takes minutes. It needs coverage.py
(`python-coverage`, installed with the `10_sre_devops` packages). A clone set
up before this hook moved needs `pre-commit install` again to install the
pre-push hook.

GitLab, GitHub, and Gitea share the scripts in [`scripts/ci/`](./scripts/ci/);
see the [GitHub workflows](./.github/workflows/README.md) and
[GitLab CI](./.gitlab/README.md) documentation. Pushing a `v*` tag publishes a
release with the matching [changelog](./CHANGELOG.md) section. The repository
is mirrored on [GitLab](https://gitlab.com/pad92/dotfiles),
[GitHub](https://github.com/pad92/dotfiles), and
[Codeberg](https://codeberg.org/pad7/.dotfiles).

_Maintained by [pad](https://gitlab.com/pad92) since 2015._
