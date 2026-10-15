# My Dotfiles

Linux desktop configuration for Arch Linux and CachyOS, built around Hyprland,
Zsh, Neovim, Alacritty, tmux, Waybar, and Mako.

![Hyprland desktop with Neovim, Waybar and Fastfetch on CachyOS](./dist/hyprland.webp)

[Changelog](./CHANGELOG.md) · [Releases](https://gitlab.com/pad92/dotfiles/-/releases) · [Arch installation guide](./dist/arch/install.md)

## Installation

```sh
git clone https://gitlab.com/pad92/dotfiles.git ~/.dotfiles
cd ~/.dotfiles
./install
```

Install `ansible-playbook` first. Run the installer from a terminal as a regular
user with `sudo` access. It can install fonts, Hyprland, generation-specific GPU
drivers, container and infrastructure tools, and Steam. Packages already
installed are skipped.
Choose only the groups that match the machine's hardware and software needs.
Before selecting Steam or any group containing `lib32-*` packages, enable
`[multilib]` as described in the
[Arch installation guide](./dist/arch/install.md#package-manager).

The playbook selects package groups without prompting. On Arch, it selects the
base, GTK, and Hyprland groups, then adds GPU driver groups detected from PCI
facts. Set `packages_host_groups` in `ansible/host_vars/localhost.yml` to choose
groups by `ansible_hostname`; each list replaces the defaults. For a one-time
override, pass `-e packages_group_selection=...`. Hybrid Intel/NVIDIA systems
receive both GPU groups. Canon and Samsung printer drivers are separate from
the generic printer stack. Docker and Podman, and OpenTofu and Terraform, are
also selected separately.

The installer uses `paru` or `yay` if either is already available. Otherwise, it
can build `yay-bin` for you. If you decline, it skips the AUR packages.
On Arch, installing selected repository packages does not upgrade the whole
system by default; pass `-e packages_upgrade_system=true` to include a full
`pacman -Syu`.

Package installation is additive by default. Run `./install --check` to preview
changes. To review packages installed by this repository that are no longer
selected, run `./install -e packages_action=reconcile`. Reconciliation does not
claim packages that predate its state file and requires explicit confirmation
before removal.

GPU groups are added only when the playbook can classify every controller. If
detection is incomplete, it keeps the OS defaults. Arch enables the base, GTK,
and Hyprland groups by default; Debian, Ubuntu, and Fedora use their supported
base and GTK mappings.

On Arch Linux and CachyOS, `./install` also writes a makepkg drop-in that enables
native CPU tuning and sets build parallelism to half the online processor count.
Packages built with native tuning may not run on computers with a different CPU.

Ansible installs package groups and dotfiles through
[`ansible/roles/dotfiles/`](./ansible/roles/dotfiles/). The role copies static
configuration from `files/home/`, renders host-aware files from `templates/`,
and links the Vim, tmux, and Zsh source trees into the home directory. Edit
these role files to change the configuration. `./install` passes its arguments
to `ansible-playbook`, including options such as `--check`,
`--ask-become-pass`, `--tags`, and `-e`.

The playbook initializes Git submodules at the revisions recorded in the
repository and selects a Waybar configuration for the current hostname. Vim
plugins are updated only when requested with
`-e dotfiles_update_vim_plugins=true`.

When deployment replaces a conflicting regular file or directory that has the
wrong type, it moves that path to a `.bak` sibling. Existing symbolic links at
managed paths are removed without saving the link itself; the linked-to target
is left untouched. If you need to keep a symbolic link, move or rename it before
running the installer.

The playbook supports Arch Linux and CachyOS, Debian and Ubuntu, and Fedora.
Package mappings are in `ansible/roles/packages/vars/`, with a file for each
supported OS family. Selecting an unmapped group reports an error.

GPU-driver removal also requires reconcile mode, recorded ownership, a safe
pacman transaction preview, and explicit confirmation. Packages installed
outside the installer remain unmanaged.

For the editor configuration only:

```sh
curl -sSL https://gitlab.com/pad92/dotfiles/-/raw/main/scripts/vim.sh | bash
```

A [packaged editor configuration](https://gitlab.com/pad92/dotfiles/-/jobs/artifacts/main/download?job=package_vim)
is also available.

## Customization

Set your Git identity in `~/.gitconfig.local`, which [`.gitconfig`](./ansible/roles/dotfiles/files/home/.gitconfig)
includes without tracking it:

```ini
[user]
    name = Your Name
    email = your.email@example.com
    signingkey = your_ssh_or_gpg_key
```

| Configuration                                                              | What to change                                                      |
| :------------------------------------------------------------------------- | :------------------------------------------------------------------ |
| [`.zshenv`](./ansible/roles/dotfiles/files/home/.zshenv), [`.zprofile`](./ansible/roles/dotfiles/files/home/.zprofile), [`.zshrc`](./ansible/roles/dotfiles/templates/home/.zshrc.j2) | Shell environment, desktop login, plugins, and aliases              |
| [`.config/uwsm/`](./ansible/roles/dotfiles/files/home/.config/uwsm/)                                                    | Shared session environment and compositor-specific GPU settings     |
| [`.config/hypr/`](./ansible/roles/dotfiles/files/home/.config/hypr/)                                                    | Bindings, window rules, and `hosts/<hostname>.lua` hardware layouts |
| [`hyprtoolkit.conf`](./ansible/roles/dotfiles/files/home/.config/hypr/hyprtoolkit.conf)                                 | Toolkit colors, fonts, GTK/icon themes, and geometry                |
| [`.config/waybar/`](./ansible/roles/dotfiles/files/home/.config/waybar/)                                                | Status bar, including per-host configurations                       |
| [`.config/alacritty/`](./ansible/roles/dotfiles/files/home/.config/alacritty/), [`.tmux.conf`](./ansible/roles/dotfiles/files/home/.tmux.conf)      | Terminal appearance and tmux bindings                               |
| [`.config/nvim/`](./ansible/roles/dotfiles/files/home/.config/nvim/), [`.vimrc`](./ansible/roles/dotfiles/files/home/.vimrc)                        | Editor settings and plugins                                         |
| [`.config/awww/`](./ansible/roles/dotfiles/files/home/.config/awww/)                                                    | Local and remote wallpaper sources                                  |
| `~/.local/share/backgrounds/`                                              | Local images for wallpaper rotation                                 |

Shell settings include `LANG`, `EDITOR`, and the Oh My Zsh plugin list. The common
UWSM environment defines `BROWSER`, `TERMINAL`, and `XCURSOR_THEME`, while
`env-hyprland` contains host-specific GPU settings such as `AQ_DRM_DEVICES` and
Vulkan drivers. Hyprland host files define
monitor layouts and workspace mappings; Waybar uses `config.PadsTower` and
`config.PadsP5560` for different hardware.

Alacritty settings cover fonts, spacing, opacity, and colors. For Hyprland Lua
validation and completion, see
[`home/.config/hypr/.luarc.json`](./ansible/roles/dotfiles/files/home/.config/hypr/.luarc.json).
Electron 38.2 and later use native Wayland by default in a Wayland session, as
described in the
[Electron Wayland notes](https://www.electronjs.org/blog/tech-talk-wayland).
This repository's `~/.config/electron-flags.conf` contains no required flags.

## Shell and editors

Zsh uses Oh My Zsh with the `docker`, `ansible`, `git`, `vscode`, and `thefuck`
plugins, along with autosuggestions and syntax highlighting. The configuration
also sets up shell history, prompt themes, and `$HOME/.bin` in `PATH`.

### Custom aliases and functions

Aliases are defined in
[`zsh/init/aliases.zsh`](./ansible/roles/dotfiles/files/home/zsh/init/aliases.zsh).
Shell functions load from
[`zsh/functions/`](./ansible/roles/dotfiles/files/home/zsh/functions/).

| Alias                            | Command                                 |
| :------------------------------- | :-------------------------------------- |
| `terraform`                      | `tofu`, when available                  |
| `mediasync`                      | Home media server sync script           |
| `backup`                         | `~/.bin/backup.sh`                      |
| `steam-opt`                      | `steam-optimize`                        |
| `mirrored`, `mirrors`, `mirrora` | `mirror` sorted by delay, score, or age |

Common functions:

| Command                                      | Purpose                                                                                  |
| :------------------------------------------- | :--------------------------------------------------------------------------------------- |
| `arch_update`                                | Run system, firmware, Flatpak, and orphan/cache updates; report failed steps             |
| `clean_arch`                                 | Remove orphan packages, clean pacman/yay caches, and find `.pacnew` / `.pacsave` files   |
| `mirror [delay\|score\|age]`                 | Select and rank French Arch mirrors with `reflector`                                     |
| `extract <file>`                             | Unpack archives including `.tar.bz2`, `.tgz`, `.zip`, `.rar`, and `.7z`                  |
| `gpg-encrypt <file/dir>` / `gpge`            | Encrypt files or directories recursively; prompt for the GPG email                       |
| `gpg-decrypt <file/dir>` / `gpgd`            | Decrypt files or directories and extract `.tar.gz.gpg` / `.tgz.gpg` archives             |
| `md5`, `sha1`, `sha256`, `sha512` `<string>` | Hash a string with OpenSSL                                                               |
| `ssh-copy-agent-keys [user@host]`            | Select keys from `ssh-agent` and add them to remote `authorized_keys` without duplicates |
| `ip_a`, `ip_l`, `ip_p`                       | Show all, local, or public IP information                                                |
| `curl_time <url>`                            | Measure DNS, connection, first-byte, and total HTTP timings                              |
| `meteo`                                      | Show the weather through `wttr.in`                                                       |
| `transfer <file>`                            | Upload to `transfer.sh` and return a shareable URL                                       |
| `youtubeEncode <file>`                       | Encode video with `libx264` and AAC for YouTube                                          |
| `radio`                                      | Listen to radio from the terminal                                                        |
| `calc "<expr>"`                              | Evaluate expressions with `bc`                                                           |
| `src`                                        | Reload the shell configuration                                                           |

Maintenance functions are in `arch.zsh`; archive and encryption helpers are in
`archive.zsh` and `crypt.zsh`. The GPG helpers preserve modification times and
offer to delete source files. Encryption uses `--trust-model always`, and
decryption restores timestamps when extracting archives.

### Shell shortcuts

Configured in [`zsh/init/key-bindings.zsh`](./ansible/roles/dotfiles/files/home/zsh/init/key-bindings.zsh):

| Shortcut               | Action                               |
| :--------------------- | :----------------------------------- |
| `Ctrl+R`               | Search backward through history      |
| `Ctrl+X Ctrl+E`        | Edit the command in `$EDITOR`        |
| `Ctrl+Left/Right`      | Move by word                         |
| `Alt+L` (`Esc L`)      | Run `ls`                             |
| `Alt+W` (`Esc W`)      | Cut text between the cursor and mark |
| `Alt+M`                | Copy the previous shell word         |
| `Up/Down` after typing | Search history by the typed prefix   |
| `PageUp/PageDown`      | Navigate history                     |
| `Home/End`             | Move to the start/end of the line    |
| `Shift+Tab`            | Cycle completion backward            |
| `Space`                | Expand history references            |

### Follow several logs

[`mtail`](./ansible/roles/dotfiles/files/home/zsh/functions/mtail.zsh) prefixes
lines with the filename and uses `tail -F` to follow files across rotation. It
prints the last 10 lines and scans for new matches every second. Quote globs to
include future files:

```zsh
mtail                              # Defaults to *.log
mtail app.log worker.log           # Specific files
mtail '*.log' '/var/log/app/*.log'  # Current and future matches
mtail 'my app.log'                 # Spaces in filenames
```

`Ctrl+C` stops the followers without closing Zsh. Requires `awk` and standard
command-line tools, not `inotify-tools`.

### Editors

[Neovim](./ansible/roles/dotfiles/files/home/.config/nvim/) is configured in Lua:

- `lazy.nvim` manages plugins and lazy loading.
- Telescope searches files, buffers, and symbols.
- `nvim-treesitter` on its `main` branch provides highlighting, indentation,
  and folding. This setup requires Neovim 0.12+.
- Native LSP (`vim.lsp.config` / `vim.lsp.enable`, available since 0.11) works
  with Mason and `nvim-cmp`. `LspAttach` sets navigation, diagnostic, and
  formatting shortcuts.
- Gitsigns shows changes in the margin and provides hunk navigation, staging,
  and blame commands.
- Gruvbox, Lualine, and vertical indentation guides define the appearance.

The [older Vim setup](./ansible/roles/dotfiles/files/home/.vimrc) uses Vundle, a
custom status line, filetype settings, `vim-gitgutter`, and `vim-fugitive`.
Alacritty is the terminal, and tmux includes session-management and
layout-persistence plugins.

## Desktop

The Hyprland configuration uses Lua and requires **Hyprland 0.55+**.
[`hyprtoolkit.conf`](./ansible/roles/dotfiles/files/home/.config/hypr/hyprtoolkit.conf)
defines the theme. `include/toolkit.lua` parses it, `config.lua` reads it, and
`conf/autostart.lua` applies GTK/libadwaita settings through `gsettings`. The
lock-screen colors are configured separately.

For TTY startup, see the
[session installation guide](./dist/arch/install.md#gnome-keyring-pam-setup).
It covers GNOME Keyring PAM configuration in `/etc/pam.d/login`, UWSM setup,
Zsh startup files, and systemd session services. The
[upstream systemd guide](https://wiki.hypr.land/Useful-Utilities/Systemd-start/)
provides further context.

### Main shortcuts

| Shortcut                                  | Action                                         |
| :---------------------------------------- | :--------------------------------------------- |
| `SUPER + Return`                          | Terminal                                       |
| `SUPER + E / C / W / M`                   | File manager / editor / browser / music player |
| `SUPER + Shift + Return`                  | Password manager                               |
| `SUPER + Shift + Q`                       | Close window                                   |
| `SUPER + [0-9]` / `SUPER + Shift + [0-9]` | Focus workspace / move window to workspace     |
| `SUPER + Arrows` or Vim keys              | Move focus; add `Shift` to move the window     |
| `SUPER + F` / `SUPER + ALT + Space`       | Toggle fullscreen / floating                   |
| `SUPER + L` / `SUPER + Delete`            | Lock / logout menu                             |
| `SUPER + ALT + Right`                     | Change wallpaper                               |
| `SUPER + PgUp/PgDn` / `SUPER + Home`      | Zoom in/out / reset                            |
| `Print` / `SUPER + P`                     | Screenshot                                     |

Media and brightness keys control volume, playback, and screen brightness.
Left-click Waybar's audio module to switch to the next output sink. Right-click it
to open `pavucontrol`.

### LACT profiles

[`.config/lact/config.yaml`](./ansible/roles/dotfiles/files/home/.config/lact/config.yaml) is a profile template for
PadsTower's GPU (`1002:73df-1462:3980-0000:0d:00.0`). The installer does not copy
it to `/etc/lact/config.yaml`. To use it, first back up your LACT configuration,
verify the GPU identifier in LACT, and manually merge the relevant profiles.
Review the fan curves for your hardware before applying them.

### Wallpapers and lock screen

[`awww.sh`](./ansible/roles/dotfiles/files/home/.bin/awww.sh) selects an image
for each monitor from local files or an existing NFS/CIFS mount. Photos keep
their aspect ratio, use a blurred copy as the background, and show the date and
city when metadata is available. Rendering accounts for each monitor's scale
factor on mixed-DPI setups. In `auto` mode, an unavailable, empty, or slow
remote source falls back to local images.

Copy the sample to create the Git-ignored configuration. The script reloads it
each time it runs and uses the sample itself when the local file is absent.

```sh
cp ~/.config/awww/awww.conf-sample ~/.config/awww/awww.conf
```

The sample documents multiple local and remote source directories, NFS/CIFS
mounts, timeouts, and troubleshooting commands.

Generated renders live in `managed-v1/` under `AWWW_RENDER_CACHE_DIR`. The cache
removes unreferenced renders older than 30 days and evicts the oldest remaining
renders above `AWWW_RENDER_CACHE_MAX_BYTES` (2 GiB by default). Wallpaper and
carousel references are preserved, even if they alone exceed the quota; the
script then prints a warning. Files outside this managed directory, including
older renders from previous versions, are left for manual cleanup. ImageMagick
is required even with effects disabled, to reject missing or corrupt images.

Put fallback images in `~/.local/share/backgrounds/`. For example, this command
copies images tagged `paysage` from another directory:

```sh
exiftool -q -if '$Keywords =~ /paysage/' -r ${SRC_DIR} \
    -o "${XDG_DATA_HOME:-$HOME/.local/share}/backgrounds/"
```

`awww.service` starts with Hyprland, and `awww_random.timer` changes wallpapers
every 30 minutes. Apply changes with:

```sh
systemctl --user restart awww_random.service
```

[Hyprlock](./ansible/roles/dotfiles/templates/home/.config/hypr/hyprlock.conf.j2) shows the time, system batteries, and
current media. Player text and artwork refresh every 3 seconds; battery status
refreshes every 10 seconds.

Choose **Carousel** in Wlogout to lock with photos from the configured AWWW
sources. The background advances every minute and uses AWWW's blur and metadata
settings. Each image update tries at most three images per source. In `auto`
mode, failed remote reads fall back to local images. A helper invocation has a
25-second deadline, followed by at most two seconds for forced termination;
`CAROUSEL_TIMEOUT_SECONDS` can override the deadline (minimum 3 seconds).
If the update fails, the previous background remains available.

For media playing in Firefox or Chrome, the source label reads `xesam:url` and
shows the service name instead of the browser. Known services such as Deezer and
YouTube get their own icon. Other valid domains use a globe, while missing or
invalid URLs fall back to the browser name.

The [helper scripts](./ansible/roles/dotfiles/files/home/.config/hypr/hyprlock/) read metadata with `playerctl`,
download HTTPS covers with `curl`, and resize them to 150 × 150 with ImageMagick.
Downloads and conversions have size, time, and resource limits. Covers are
cached by URL under `$XDG_RUNTIME_DIR`, or in a private `${TMPDIR:-/tmp}`
directory when no runtime directory is available. A cached cover stays on
screen if refreshing that same URL fails or Firefox deletes its temporary image.
When there is no usable cover for the current URL, Hyprlock displays a
transparent image.

Battery readings come from `/sys/class/power_supply` and exclude peripherals.
Colors and positions are configured in `hyprlock.conf`.

## Scripts

The role deploys the script collection from
[`ansible/roles/dotfiles/files/home/.bin/`](./ansible/roles/dotfiles/files/home/.bin/)
to `~/.bin/`, which is added to `PATH` by Zsh.

| Script                                                     | Purpose                                                                                                                                                                                                                                       |
| :--------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`steam-optimize`](./ansible/roles/dotfiles/files/home/.bin/steam-optimize) (`steam-opt`) | Python 3 game launcher with monitor detection, RADV/Vulkan ICD/Mesa layer settings, per-game overrides, Gamescope, and session cleanup |
| [`backup.sh`](./ansible/roles/dotfiles/files/home/.bin/backup.sh) (`backup`) | Back up with rsync and SSH agent authentication, report Arch orphans without removing them, estimate added and deleted file sizes and full sizes of changed files, and apply [exclude patterns](./dist/backup_excludes.txt) to remote pruning |
| [`awww.sh`](./ansible/roles/dotfiles/files/home/.bin/awww.sh) | Select a wallpaper per monitor from local files or an available NFS/CIFS mount |
| [`razer_dpi.py`](./ansible/roles/dotfiles/files/home/.bin/razer_dpi.py) | Manage Razer mouse DPI |
| [`hypr-screenshot.sh`](./ansible/roles/dotfiles/files/home/.bin/hypr-screenshot.sh) | Capture the desktop showcase in a nested compositor with `make screenshot` |
| [`comcut`](./ansible/roles/dotfiles/files/home/.bin/comcut), [`comskip.sh`](./ansible/roles/dotfiles/files/home/.bin/comskip.sh) | Detect and remove commercial breaks with comskip/ffmpeg, adapted from [comchap](https://github.com/BrettSheleski/comchap) |
| [`diff-cmd`](./ansible/roles/dotfiles/files/home/.bin/diff-cmd) | Compare a command's output for two arguments using the `IN` placeholder |
| [`vscodium_ext.sh`](./ansible/roles/dotfiles/files/home/.bin/vscodium_ext.sh) | Install VSCodium extensions |

## CI and releases

The repository is mirrored on GitHub, GitLab, and a self-hosted Gitea instance.
All three use shared scripts in [`scripts/ci/`](./scripts/ci/).

| Forge  | Pipeline                                     | Documentation                                     |
| :----- | :------------------------------------------- | :------------------------------------------------ |
| GitHub | [`.github/workflows/`](./.github/workflows/) | [Workflows README](./.github/workflows/README.md) |
| GitLab | [`.gitlab-ci.yml`](./.gitlab-ci.yml)         | [GitLab CI README](./.gitlab/README.md)           |
| Gitea  | Reuses `.github/workflows/`                  | See the Workflows README                          |

[`scripts/ci/build_pages.sh`](./scripts/ci/build_pages.sh) builds the README,
changelog, installation guide, and CI documentation into a static site. It also
backs the local `post-commit` preview hook. The CI pages are published at
`/github/workflows/README.md/` and `/.gitlab/README.md/`; the GitHub path loses its
leading dot because `actions/upload-pages-artifact` strips `.github` from the
published archive.

Tags matching `v*` publish a release using the matching changelog section,
extracted by [`scripts/ci/extract_release_notes.sh`](./scripts/ci/extract_release_notes.sh).

## Application ecosystem

| Category              | Tools                      |
| :-------------------- | :------------------------- |
| Shell                 | Zsh                        |
| Editors               | Neovim, Vim, VSCode        |
| Terminal and sessions | Alacritty, tmux            |
| Desktop tools         | Waybar, hyprlauncher, Mako |
| Passwords             | Proton Pass CLI            |
| System information    | Fastfetch, Htop            |

_Maintained by [pad](https://gitlab.com/pad92)🐐 with ❤️ since 2015 (11+ years)_
