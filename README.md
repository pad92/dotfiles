# My Dotfiles Collection

This repository contains my curated personal configuration files (dotfiles) for various operating systems and environments. It aims to provide a robust, reliable, and highly customized foundation for modern Linux desktop usage.

## 🚀 Quick Start

### Install everything
This script performs a full setup, applying all configurations and managing necessary installations.
```sh
git clone https://gitlab.com/pad92/dotfiles.git ~/.dotfiles
cd ~/.dotfiles
./install
```

### Install only VIM/Editor
To set up your preferred editor without installing everything else:
```sh
curl -sSL https://gitlab.com/pad92/dotfiles/-/raw/main/vim.sh | sh
```

## 🔧 System Utilities & Scripts

A collection of custom shell scripts and utilities housed in the `bin/` directory.

*   **`backup.sh`**: Utility for system backups.
*   **`xrandr.sh`**: Script for managing display and resolution.
*   **`razer_dpi.py`**: Python utility for Razer peripheral DPI management.
*   Includes zsh functions for system maintenance (e.g., `clean_arch`, `arch_update`) and media handling (e.g., `extract`, `mediasync`).

## 🖥️ Desktop Environments & Window Managers

### Hyprland
My current primary Window Manager configuration.
> [!WARNING]
> **Breaking Change Warning**: The Hyprland configuration in this repository has migrated to Lua. These configurations are compatible with **Hyprland v0.55 and above**. Using these files with older versions will result in configuration errors.

*   **Configuration**: Located in `.config/hypr`
*   **Wallpaper**: Place wallpapers into `~/.local.share/backgrounds`
*   **Batch upload tip**:
    ```sh
    exiftool -q -if '$Keywords =~ /paysage/' -r ${SRC_DIR} -o "${XDG_DATA_HOME}/backgrounds/"
    ```

### ⌨️ Hyprland Keybindings
| Shortcut | Action |
| :--- | :--- |
| `SUPER + Return` | Terminal |
| `SUPER + E` | File manager |
| `SUPER + C` | Code editor |
| `SUPER + W` | Browser |
| `SUPER + M` | Music Player |
| `SUPER + D` | Application menu |
| `SUPER + SHIFT + Return` | Password Manager |
| `SUPER + SHIFT + Q` | Close window |
| `SUPER + F` | Fullscreen |
| `SUPER + L` | Lock |
| `SUPER + Delete` | Logout menu |
| `SUPER + ALT + Space` | Float/Tile |
| `SUPER + SHIFT + F` | Toggle Float |
| `SUPER + ALT + Right` | Change wallpaper |
| `SUPER + SHIFT + V` | Clipboard history |
| `SUPER + [1-9]` | Focus workspace |
| `SUPER + SHIFT + [1-9]` | Move window to workspace |
| `CTRL + SUPER + Right/Left` | Next/Prev workspace |
| `SUPER + [Arrows/Vim keys]` | Focus window |
| `SUPER + SHIFT + [Arrows/Vim keys]` | Move window |
| `Print` / `SUPER + P` | Screenshot |
| `XF86Audio...` | Audio Controls |
| `XF86Mon...` | Brightness Controls |

### i3 & Sway
Legacy/Alternative configurations are available in `.config/i3` and `.config/sway` for testing or alternative setups.

## ⚙️ Tool-Specific Configurations

### 🐚 Shell (Zsh)
Zsh is configured for maximum efficiency with advanced features:
*   **Plugins**: Uses `oh-my-zsh` with plugins for `docker`, `ansible`, `git`, `vscode`, `thefuck`, and syntax highlighting/autosuggestions.
*   **Customization**: Features extensive history management, custom prompt themes, and path exports for custom binaries (`$HOME/.bin`).

### 📖 Editor (Vim)
A highly configured editor built with `vundle` and `gruvbox` color scheme.
*   **Key Features**: Advanced statusline customization, robust filetype detection, and modern plugin support (e.g., `vim-gitgutter`, `vim-fugitive`).

### 💾 Terminal & Session Management
*   **Terminal Emulator**: Configured for Kitty and Alacritty.
*   **Multiplexer**: `tmux` is set up with plugins for session management and layout persistence.

### ⌨️ Application Ecosystem
A comprehensive list of configured tools:
*   **Shell**: Zsh
*   **Editor**: Vim
*   **Terminal**: Kitty, Alacritty
*   **Multiplexer**: Tmux
*   **UI/UX**: Waybar, Rofi, Wofi, Dunst, Mako (A modern, complete look-and-feel stack.)
*   **System**: Fastfetch, Htop (Provides system information and resource monitoring.)
*   **IDE/Editor**: VSCode has specific settings applied via `settings.json`.

## 📦 OS Specifics & Maintenance

### Arch Linux
My primary and main driver.
*   **Installation Guide**: See the full, detailed guide: [Arch Linux / CachyOS Installation Guide](./dist/arch/install.md).
*   **Maintenance**: Includes specialized scripts like `arch_update` for full system updates and cleaning old pacman files) and `mirror` functions for mirrorlist management.

### Ubuntu
Compatible configurations are provided.

---
*Maintained by [pad](https://gitlab.com/pad92)🐐 with ❤️ since 2015 (11+ years)*
