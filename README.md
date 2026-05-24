# My Dotfiles Collection

This repository contains my curated personal configuration files (dotfiles) for various operating systems and environments. It aims to provide a robust, reliable, and highly customized foundation for modern Linux desktop usage.

## 🚀 Installation & Quick Start

For the latest updates, check the [Changelog](./CHANGELOG.md).
You can also download the current version directly from [here](https://gitlab.com/pad92/dotfiles/-/releases).

### Full Setup
This script performs a full setup, applying all configurations and managing necessary installations.
```sh
git clone https://gitlab.com/pad92/dotfiles.git ~/.dotfiles
cd ~/.dotfiles
./install
```

### Editor Only
To set up the editor configuration without installing the full suite:
```sh
curl -sSL https://gitlab.com/pad92/dotfiles/-/raw/main/vim.sh | sh
```

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

### 📖 Editor (Vim)
A highly configured editor built with `vundle` and the `gruvbox` color scheme.
*   **Quick Install**: You can download the pre-packaged configuration from the [CI Artifacts page](https://gitlab.com/pad92/dotfiles/-/jobs/artifacts/main).
*   **Key Features**: Advanced statusline customization, robust filetype detection, and modern plugin support (e.g., `vim-gitgutter`, `vim-fugitive`).

### 💾 Terminal & Session Management
*   **Terminal Emulators**: Optimized configurations for **Kitty** and **Alacritty**.
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

### 🔑 TTY Launch & Session Integration
When launching from a tty instead of a display manager, some session integrations that display managers normally handle may not be configured. One common example is GNOME Keyring - if `pam_gnome_keyring.so` is not present in your PAM login configuration, the keyring will not auto-unlock, and applications may prompt you to unlock it manually.

To set this up, add the `pam_gnome_keyring.so` lines to the PAM configuration file used by your login method (e.g. `/etc/pam.d/login` for `login(1)`). Consult your distribution’s documentation for the correct file and syntax. For example, on Arch Linux:

```
#%PAM-1.0

auth       requisite    pam_nologin.so
auth       include      system-local-login
-auth      optional     pam_gnome_keyring.so
account    include      system-local-login
password   include      system-local-login
-password  optional     pam_gnome_keyring.so    use_authtok
session    include      system-local-login
-session   optional     pam_gnome_keyring.so    auto_start
```

For more details, see: [Hyprland Wiki - Systemd-start in TTY](https://wiki.hypr.land/Useful-Utilities/Systemd-start/#in-tty)

## 📦 System Utilities & OS Specifics

### 🔧 Custom Scripts
A collection of shell scripts and utilities located in the `bin/` directory:
*   **`backup.sh`**: System backup utility.
*   **`xrandr.sh`**: Display and resolution management.
*   **`razer_dpi.py`**: Razer peripheral DPI management.
*   **Zsh Functions & Aliases**: See the comprehensive [Custom Aliases & Functions](#-custom-aliases--functions) section for a detailed list of system maintenance, utility, and archive handling scripts.

### 🐧 OS Maintenance
*   **Arch Linux (Primary)**:
    *   Detailed installation guide: [Arch Linux / CachyOS Installation Guide](./dist/arch/install.md).
    *   Includes `arch_update` for full system updates and `mirror` functions for mirrorlist management.
*   **Ubuntu**: Compatible configurations provided.

## 📋 Application Ecosystem Summary

A comprehensive list of configured tools across the stack:

| Category | Tools |
| :--- | :--- |
| **Shell** | Zsh |
| **Editor** | Vim, VSCode |
| **Terminal** | Kitty, Alacritty |
| **Multiplexer** | Tmux |
| **UI/UX** | Waybar, Wofi, Mako |
| **System** | Fastfetch, Htop |

---
*Maintained by [pad](https://gitlab.com/pad92)🐐 with ❤️ since 2015 (11+ years)*
