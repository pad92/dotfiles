# My Dotfiles Collection

This repository contains my curated personal configuration files (dotfiles) for various operating systems and environments. It aims to provide a robust, reliable, and highly customized foundation for modern Linux desktop usage.

## 🚀 Installation & Quick Start

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

### 📖 Editor (Vim)
A highly configured editor built with `vundle` and the `gruvbox` color scheme.
*   **Key Features**: Advanced statusline customization, robust filetype detection, and modern plugin support (e.g., `vim-gitgutter`, `vim-fugitive`).

### 💾 Terminal & Session Management
*   **Terminal Emulators**: Optimized configurations for **Kitty** and **Alacritty**.
*   **Multiplexer**: `tmux` configured with plugins for session management and layout persistence.

## 🖥️ Desktop Environment & Window Management

### ⌨️ Unified Keybindings
| Shortcut                            | Action                   | WM       |
| :---------------------------------- | :----------------------- | :------- |
| `SUPER + Return`                    | Terminal                 | All      |
| `SUPER + Shift + Q`                 | Close window             | All      |
| `SUPER + [1-9]`                     | Focus workspace          | All      |
| `SUPER + Shift + [1-9]`             | Move window to workspace | All      |
| `SUPER + [Arrows/Vim keys]`         | Focus window             | All      |
| `SUPER + Shift + [Arrows/Vim keys]` | Move window              | All      |
| `SUPER + F`                         | Fullscreen toggle        | All      |
| `XF86Audio...`                      | Audio Controls           | All      |
| `XF86Mon...`                        | Brightness Controls      | All      |
| `SUPER + E`                         | File manager             | Hyprland |
| `SUPER + C`                         | Code editor              | Hyprland |
| `SUPER + W`                         | Browser                  | Hyprland |
| `SUPER + M`                         | Music Player             | Hyprland |
| `SUPER + Shift + Return`            | Password Manager         | Hyprland |
| `SUPER + L`                         | Lock                     | Hyprland |
| `SUPER + Delete`                    | Logout menu              | Hyprland |
| `SUPER + ALT + Space`               | Float/Tile               | Hyprland |
| `SUPER + SHIFT + F`                 | Toggle Float             | Hyprland |
| `SUPER + ALT + Right`               | Change wallpaper         | Hyprland |
| `Print` / `SUPER + P`               | Screenshot               | Hyprland |
| `SUPER + D`                         | Application menu         | i3/Sway  |
| `SUPER + Shift + V`                 | Clipboard history        | i3/Sway  |
| `SUPER + Shift + R`                 | Reload config            | i3       |
| `SUPER + Shift + E`                 | Exit i3                  | i3       |
| `Alt + Tab`                         | Next floating window     | Sway     |
| `Alt + Shift + Tab`                 | Prev floating window     | Sway     |
| `Caps Lock`                         | Caps Lock toggle         | Sway     |

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

### i3 & Sway (Alternatives)
Legacy and alternative configurations are available in `.config/i3` and `.config/sway` for testing or alternative setups.


## 📦 System Utilities & OS Specifics

### 🔧 Custom Scripts
A collection of shell scripts and utilities located in the `bin/` directory:
*   **`backup.sh`**: System backup utility.
*   **`xrandr.sh`**: Display and resolution management.
*   **`razer_dpi.py`**: Razer peripheral DPI management.
*   **Zsh Functions**: Includes system maintenance (`clean_arch`, `arch_update`) and media handling (`extract`, `mediasync`).

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
| **UI/UX** | Waybar, Rofi, Wofi, Dunst, Mako |
| **System** | Fastfetch, Htop |

---
*Maintained by [pad](https://gitlab.com/pad92)🐐 with ❤️ since 2015 (11+ years)*
