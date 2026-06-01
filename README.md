# My Dotfiles Collection

This repository contains my curated personal configuration files (dotfiles) for various operating systems and environments. It aims to provide a robust, reliable, and highly customized foundation for modern Linux desktop usage.

## 🚀 Installation & Quick Start

For the latest updates, check the [Changelog](./CHANGELOG.md).
You can also download the current version directly from [here](https://gitlab.com/pad92/dotfiles/-/releases).

### Full Setup
This repository provides automated installation workflows tailored per operating system:

*   **Arch Linux & CachyOS (Primary)**: Runs the interactive setup manager.
    ```sh
    git clone https://gitlab.com/pad92/dotfiles.git ~/.dotfiles
    cd ~/.dotfiles
    ./install
    ```
    > [!TIP]
    > **High-Fidelity Installer**: The interactive manager presents a clean menu to select package suites (Base, Fonts, GTK, Hyprland, Nvidia, Steam, etc.). It automatically skips already installed packages and configures `yay` or `paru` for AUR dependencies.

*   **Ubuntu (Noble 24.04+)**: Run the dedicated automated setup script:
    ```sh
    git clone https://gitlab.com/pad92/dotfiles.git ~/.dotfiles
    cd ~/.dotfiles
    bash dist/ubuntu/install.sh
    ```
    > [!IMPORTANT]
    > **Snap & Flatpak-Free**: The Ubuntu installer is fully compliant with a Snap-free and Flatpak-free configuration, utilizing official scoped GPG keyrings and native APT repositories to establish package parity with the Arch environment.


### Editor Only
*   To set up the editor configuration without installing the full suite:
```sh
curl -sSL https://gitlab.com/pad92/dotfiles/-/raw/main/vim.sh | sh
```
*   **Quick Install**: You can download the pre-packaged configuration from the [Artifacts](https://gitlab.com/pad92/dotfiles/-/jobs/artifacts/main/download?job=package_vim
).

## ⚙️ Customization & Personalization

To customize and adapt this dotfiles collection to your own system and identity, you should adjust the following key configuration files:

### 👤 Git Identity
*   **`~/.gitconfig.local`** *(Not tracked, created locally)*: Define your personal Git credentials here. It is automatically imported by the main [`.gitconfig`](./.gitconfig):
    ```ini
    [user]
        name = Your Name
        email = your.email@example.com
        signingkey = your_ssh_or_gpg_key
    ```

### 🐚 Shell & Environment (`Zsh`)
*   **[`.zshrc`](./.zshrc)**: Adjust primary shell configurations (e.g., local language `LANG`, default editor `EDITOR`, and the active Oh My Zsh `plugins` list).
*   **[`zsh/init/aliases.zsh`](./zsh/init/aliases.zsh)**: Add, edit, or remove terminal aliases to fit your daily workflow.

### 🖥️ Wayland & Hyprland Session
*   **[`.config/uwsm/env`](./.config/uwsm/env)**: Manage global environment variables for the Wayland session (e.g., default browser `BROWSER`, default terminal `TERMINAL`, and default cursor theme `XCURSOR_THEME`) and set hostname-specific GPU/driver optimizations (such as `AQ_DRM_DEVICES` or Vulkan driver settings).
*   **`.config/hypr/`**: Adjust window manager bindings, window rules, workspaces, and look-and-feel preferences (now migrated to Lua). Host-specific hardware layouts (such as monitor outputs and static workspace mappings) are modularly loaded from `hosts/<hostname>.lua` to maintain clean dotfiles portability.
*   **`~/.local/share/backgrounds/`**: Add your custom wallpaper image files here to integrate with desktop slideshow/randomizer scripts.

### 💻 Terminals & Tools
*   **`.config/alacritty/`**: Customize the Alacritty terminal's font, window spacing, opacity, and color palette.
*   **[`.tmux.conf`](./.tmux.conf)**: Customize keys and options for your Tmux workspace.
*   **[`.config/nvim/`](./.config/nvim/)**: Curated, modern, and modular **Neovim** configuration written from scratch in Lua.
*   **[`.vimrc`](./.vimrc)**: Adjust keybindings and plugin preferences for your core legacy Vim editor.
*   **`~/.config/electron-flags.conf`**: Consolidated configuration for all Electron-based editors (VS Code, Codium, and Antigravity IDE) to ensure optimal Wayland compatibility and native GPU acceleration across all hosts.
*   **`~/.dotfiles/.luarc.json`**: Project-specific Lua environment settings optimized for standard workspace validation and seamless autocompletion.


## 🛠️ Core Tooling

### 🐚 Shell (Zsh)
Configured for maximum efficiency with advanced features:
*   **Plugins**: Powered by `oh-my-zsh` with `docker`, `ansible`, `git`, `vscode`, `thefuck`, and syntax highlighting/autosuggestions.
*   **Customization**: Extensive history management, custom prompt themes, and path exports for custom binaries (`$HOME/.bin`).

#### ⌨️ Zsh Keyboard Shortcuts
Configured in `zsh/init/key-bindings.zsh` for maximum command line productivity:

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| `Ctrl + R` | History Search | Search backward incrementally in history |
| `Ctrl + X, Ctrl + E` | Edit Command | Edit current command line in `$EDITOR` (Vim) |
| `Ctrl + Left` | Back Word | Move cursor backward one word |
| `Ctrl + Right` | Forward Word | Move cursor forward one word |
| `Alt + L` (Esc + L) | Quick `ls` | Run the `ls` command immediately |
| `Alt + W` (Esc + W) | Kill Region | Cut/delete text from the cursor to the mark |
| `Alt + M` | Copy Shell Word | Copy the previous word on the command line |
| `Up Arrow` (after typing) | Fuzzy Search | Search history forward matching the typed prefix |
| `Down Arrow` (after typing) | Fuzzy Search | Search history backward matching the typed prefix |
| `PageUp` / `PageDown` | History Navigate | Move up/down through history lines |
| `Home` / `End` | Line Navigation | Go to the beginning/end of the line |
| `Shift + Tab` | Reverse Complete | Navigate backwards in the autocompletion menu |
| `Space` | Magic Space | Perform history expansion when pressing space |

#### 🐚 Custom Aliases & Functions
A set of highly optimized aliases and shell functions defined in `zsh/init/aliases.zsh` and autoloaded from `zsh/functions/`:

##### 📌 Handy Aliases
| Alias | Target / Command | Purpose |
| :--- | :--- | :--- |
| `terraform` | `tofu` | Uses OpenTofu as transparent replacement if available |
| `mediasync` | `~/.../tools/mediasync.py` | Sync home media server repository |
| `backup` | `~/.dotfiles/bin/backup.sh` | Trigger complete system backup script |
| `steam-opt` | `steam-optimize` | Launch Steam with performance/GPU optimizations |
| `ggc` | `git-gen-commit` | Automatically generate semantic git commit messages |
| `volmute` / `volinc` / `voldec` | `ManageSound.sh` | Convenient system audio/volume control aliases |
| `mirrord` / `mirrors` / `mirrora` | `mirror [delay/score/age]` | Quick sorting alternatives for Arch mirrorlist optimization |

##### 🛠️ Custom Shell Functions
Organized by functional modules for clean management:

###### 🐧 Arch Linux & System Maintenance (`zsh/functions/arch.zsh`)
*   **`arch_update`**: Comprehensive system upgrade. Triggers `yay -Syu --devel`, firmware update checking (`fwupdmgr`), Flatpak updates, and automated orphans/caches cleanup.
*   **`clean_arch`**: Cleans up packages orphans (`pacman -Rns`), purges pacman/yay cache (`yay -Scc`), removes old packages version caches (`paccache`), and detects outstanding `.pacnew` / `.pacsave` files.
*   **`mirror [delay|score|age]`**: Fetches, filters, and rates the fastest Arch Linux package mirrors located in France utilizing `reflector`.

###### 📁 Archives & Crypto (`zsh/functions/archive.zsh`, `crypt.zsh`)
*   **`extract <file>`**: Extract-all wrapper that intelligently decompresses any archive format (`.tar.bz2`, `.tgz`, `.zip`, `.rar`, `.7z`, etc.).
*   **`md5` / `sha1` / `sha256` / `sha512` `<string>`**: Instant, pipeline-friendly string hashing using `openssl`.

###### 🌐 Networking & Utilities (`zsh/functions/` `ip.zsh`, `meteo.zsh`, `transfer.zsh`, `curl.zsh`, `youtube.zsh`)
*   **`ip_a` / `ip_l` / `ip_p`**: Show network info (All, Local, or Public IP address).
*   **`meteo`**: Instant graphical terminal-based weather forecast using `wttr.in`.
*   **`transfer <file>`**: Fast upload of any file to `transfer.sh` and returns a direct shareable URL.
*   **`curl_time <url>`**: Detailed HTTP connection profiling (DNS lookup, connect, start-transfer, and total times).
*   **`youtubeEncode <file>`**: Re-encodes source video with optimized parameters (`libx264`, `aac`) for reliable YouTube uploads.
*   **`radio`**: Easy interactive CLI radio terminal frontend.
*   **`calc "<expr>"`**: Command-line evaluator powered by `bc`.
*   **`src`**: Sourced reloader helper for shell config.

### 📖 Editors (Vim & Neovim)

#### ⚡ Neovim (Modern & Modular)
A state-of-the-art configuration written completely in Lua from scratch, designed to turn Neovim into a blazing-fast, IDE-like developer workspace.
*   **Key Features**:
    *   **Plugin Manager**: Managed by `lazy.nvim` for fast startup and lazy loading.
    *   **Fuzzy Finder**: Built with `telescope.nvim` for rapid interactive file/buffer/symbol searching.
    *   **Syntax & AST**: Powered by `nvim-treesitter` for beautiful, precise, and fast syntax highlighting.
    *   **Native LSP**: Utilizes the modern native LSP framework (`vim.lsp.config`/`vim.lsp.enable` in Neovim 0.11+) integrated with `mason.nvim` and `nvim-cmp` for rich IDE autocompletions and go-to-definitions.
    *   **Git Integration**: Realtime changes displayed in the margin by `gitsigns.nvim`.
    *   **Aesthetics**: Sleek `gruvbox` colorscheme coupled with `lualine.nvim` statusline and vertical indentation guides.

#### 📖 Legacy Vim
My original editor configuration built with `vundle`.
*   **Key Features**: Advanced statusline customization, robust filetype detection, and classic plugin support (e.g., `vim-gitgutter`, `vim-fugitive`).

### 💾 Terminal & Session Management
*   **Terminal Emulators**: Optimized configuration for **Alacritty**.
*   **Multiplexer**: `tmux` configured with plugins for session management and layout persistence.

## 🖥️ Desktop Environment & Window Management

### ⌨️ Unified Keybindings
| Shortcut                            | Action                   |
| :---------------------------------- | :----------------------- |
| `SUPER + Return`                    | Terminal                 |
| `SUPER + Shift + Q`                 | Close window             |
| `SUPER + [1-9]`                     | Focus workspace          |
| `SUPER + Shift + [1-9]`             | Move window to workspace |
| `SUPER + [Arrows/Vim keys]`         | Focus window             |
| `SUPER + Shift + [Arrows/Vim keys]` | Move window              |
| `SUPER + F`                         | Fullscreen toggle        |
| `XF86Audio...`                      | Audio Controls           |
| `XF86Mon...`                        | Brightness Controls      |
| `SUPER + E`                         | File manager             |
| `SUPER + C`                         | Code editor              |
| `SUPER + W`                         | Browser                  |
| `SUPER + M`                         | Music Player             |
| `SUPER + Shift + Return`            | Password Manager         |
| `SUPER + L`                         | Lock                     |
| `SUPER + Delete`                    | Logout menu              |
| `SUPER + ALT + Space`               | Float/Tile               |
| `SUPER + SHIFT + F`                 | Toggle Float             |
| `SUPER + ALT + Right`               | Change wallpaper         |
| `Print` / `SUPER + P`               | Screenshot               |

### Hyprland (Primary)
My current primary Window Manager configuration.
> [!WARNING]
> **Breaking Change**: The Hyprland configuration has migrated to Lua. These files are compatible with **Hyprland v0.55 and above**.

*   **Configuration**: Located in `.config/hypr`
*   **Wallpapers**: Place images into `~/.local/share/backgrounds`
*   **Batch upload tip**:
    ```sh
    exiftool -q -if '$Keywords =~ /paysage/' -r ${SRC_DIR} -o "${XDG_DATA_HOME}/backgrounds/"
    ```
*   **Wallpaper Daemon (`awww`)**: Wallpaper loading and randomization are fully managed via standard Systemd user services under `graphical-session.target`:
    *   **`awww.service`**: Systemd user service wrapper for the `awww-daemon`. It is robustly configured to prevent startup race conditions in Wayland by waiting for the `$WAYLAND_DISPLAY` socket (`ExecStartPre`) and clearing stale sockets, running with `--no-cache` to prevent BrokenPipe and SIGABRT crashes.
    *   **`awww_random.timer`**: Triggers `awww_random.service` (which executes [`awww.sh`](./bin/awww.sh)) every 15 minutes to automatically rotate the wallpapers across all connected monitors.
    *   **Manual Trigger**: Force wallpaper randomization at any time with `systemctl --user start awww_random.service`, or use the `SUPER + ALT + Right` keyboard shortcut.


### 🔑 TTY Launch & Session Integration

When launching Hyprland from a TTY, PAM and session management must be configured to support services like GNOME Keyring auto-unlock and UWSM session wrapping.

For a detailed, step-by-step setup covering:
- **GNOME Keyring PAM configuration** (`/etc/pam.d/login`)
- **UWSM (Universal Wayland Session Manager) installation and setup**
- **TTY shell profile/rc integration (`~/.zshrc` or `~/.zprofile`)**
- **Systemd graphical session target and application autostart**

See the [Arch Linux Installation Guide - UWSM & PAM Setup](./dist/arch/install.md#gnome-keyring-pam-setup).

Refer to the [Hyprland Wiki - Systemd startup](https://wiki.hypr.land/Useful-Utilities/Systemd-start/) for official upstream details.

## 📦 System Utilities & OS Specifics

### 🔧 Custom Scripts
A collection of highly optimized Python, Bash, and shell scripts located in the [`bin/`](./bin/) directory:
*   **[`steam-optimize`](./bin/steam-optimize)**: Advanced, monitor-aware **Python 3** wrapper for launching Steam games with customized environment variables (e.g. RADV, Vulkan ICD, Mesa layers), game-specific overrides, and dynamic Gamescope integration.
*   **[`git-gen-commit`](./bin/git-gen-commit)**: Intelligent, AI-powered git helper that generates high-quality semantic commit messages automatically.
*   **[`awww.sh`](./bin/awww.sh)**: A robust wallpaper randomizer script that integrates seamlessly with the `awww` daemon, utilizing `shuf -z` and `mapfile` to safely load distinct wallpapers per monitor.
*   **[`backup.sh`](./bin/backup.sh)**: Complete, high-performance system and configurations backup utility powered by `rsync`.
*   **[`razer_dpi.py`](./bin/razer_dpi.py)**: Convenient Razer peripherals DPI management tool.
*   **[`ManageSound.sh`](./bin/ManageSound.sh)**: Handy script for volume control and dynamic audio output switching.
*   **Zsh Functions & Aliases**: See the comprehensive [Custom Aliases & Functions](#-custom-aliases--functions) section for a detailed list of system maintenance, utility, and archive handling scripts.

### 🐧 OS Maintenance
*   **Arch Linux (Primary)**:
    *   Detailed installation guide: [Arch Linux / CachyOS Installation Guide](./dist/arch/install.md).
    *   Includes `arch_update` for full system updates and `mirror` functions for mirrorlist management.
*   **Ubuntu (Noble 24.04+)**:
    *   Setup Script: [dist/ubuntu/install.sh](./dist/ubuntu/install.sh) - Modern, idempotent, secure, and Snap-free.
    *   Provides complete bootstrapping, registers scoped GPG repositories (Docker, VS Codium, Spotify, Hashicorp, 1Password), and enables `universe` to establish package parity with the Arch Linux Hyprland 0.55+ ecosystem.

## 📋 Application Ecosystem Summary

A comprehensive list of configured tools across the stack:

| Category | Tools |
| :--- | :--- |
| **Shell** | Zsh |
| **Editor** | Vim, VSCode |
| **Terminal** | Alacritty |
| **Multiplexer** | Tmux |
| **UI/UX** | Waybar, Wofi, Mako |
| **System** | Fastfetch, Htop |

---
*Maintained by [pad](https://gitlab.com/pad92)🐐 with ❤️ since 2015 (11+ years)*
