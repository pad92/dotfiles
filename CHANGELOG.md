# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **Hyprland**: Add `hyprlauncher` support as the primary desktop application launcher and clipboard history picker.
- **Theming**: Add `hyprtoolkit.conf` to configure global `hyprtoolkit` aesthetics matching the Gruvbox colorscheme (using `0xAARRGGBB` hex color format).
- **Neovim**: Add StyLua configuration file `stylua.toml` to support local code validation.
- **Hyprland**: Add modular helper scripts in `.config/hypr/include/` to encapsulate configuration loading (`toolkit.lua`), host configuration loading (`host.lua`), and core layout/utility helpers (`utils.lua`).
- **Alacritty**: Add `Shift+Return` keyboard binding to send escape sequence for improved terminal compatibility.

### Changed
- **Hyprland**: Refactor Lua configurations to dynamically parse and source appearance, typography, and color settings from `hyprtoolkit.conf` with automatic hex format translation and fallbacks.
- **Hyprland**: Modularize and factorize main entrypoint and component sub-configurations (`.config/hypr/conf/input.lua`, `.config/hypr/conf/layout.lua`, `.config/hypr/conf/appearance.lua`) to eliminate duplicate config parameters and structural redundancy.
- **Hyprland**: Optimize workspace bindings in `.config/hypr/conf/keybindings.lua` by lifting hardware keycode allocations out of loops and extending support to a 10th workspace mapped to key `0` and numpad `0`.
- **Hyprland**: Guard device-specific input overrides to only apply when a device name is configured, and remove hardcoded placeholder device entry.
- **Hyprland**: Fix fullscreen keybinding syntax and remove stale Rofi references from window rules and blur layers.
- **Hyprland**: Fix `hypridle` DPMS commands to use proper `hyprctl dispatch dpms on/off` syntax instead of invalid Lua dispatch calls.
- **Hyprland**: Fix typos in `hyprlock` comment and `playerctlock.sh` messages and usage output.
- **Neovim**: Migrate from deprecated `vim.loop` to `vim.uv` API, consolidate backup/writebackup options removing redundant swap directory setup, and change `nvim-cmp` confirm behavior to not auto-select the first completion item.
- **Waybar**: Remove legacy Sway workspace, mode, and taskbar module definitions from configuration; retain Hyprland-only modules.
- **Waybar**: Fix `spotify` module string comparison, variable quoting, icon, and JSON output (now uses `jq`); fix `headsetcontrol` shebang to `bash`.
- **Zsh**: Harden `.zshrc` with proper variable quoting, remove duplicate `compinit` call, remove bash-specific `HISTCONTROL`/`HISTIGNORE` variables, and fix `fastfetch` detection using `command -v`.
- **Electron**: Remove redundant `--ozone-platform-hint=auto` flag from Chrome/Electron configuration, keeping explicit `--ozone-platform=wayland`.
- **Backup Utility**: Switch shebang to `bash`, use `$XDG_RUNTIME_DIR` for SSH control socket, and change `yay -Scc` to `yay -Sc` to preserve non-package caches.
- **Scripts**: Fix shell quoting and test syntax in `comcut`, replace `eval` with safer `bash -c` in `diff-cmd`, and simplify DPI logic in `razer_dpi.py`.
- **Steam-Optimize**: Add signal handling (`SIGTERM`/`SIGHUP`) and `atexit` cleanup for robust session teardown, propagate game exit code, track mouse DPI changes, add `gamescope`/`game-performance` availability checks, factor shared Forza Horizon profile, defer DND activation until after startup, create `.bak` backups before writing VDF configs, and specify `utf-8` encoding on all file operations.

### Removed
- **Wofi**: Clean up and remove all wofi configuration files (`.config/wofi`) and package installer entries.
- **Kanshi**: Remove legacy Sway/Kanshi monitor profile configuration (`.config/kanshi/config`).
- **Systemd**: Remove legacy X11 `xautolock.service` unit file.
- **Wlogout**: Remove unused icon assets (`hibernate-hover1.png`, `moon_865813.png`, `sleep2.png`).

## [v5.3.1](https://gitlab.com/pad92/dotfiles/-/releases/v5.3.1)

### Added
- **Backup Utility**: Introduce remote disk space delta calculation and log file size changes upon backup completion.
- **Installer**: Add post-installation hook (`apply_live_changes`) to dynamically rebuild font cache, reload X resources (`xrdb`), and refresh desktop environments (Mako, Waybar).

### Changed
- **System Fonts**: Standardize system-wide body and desktop environment UI fonts (GTK, Hyprland, Mako, wlogout, wofi) to **DejaVu Sans** and terminal/code blocks to **JetBrainsMono Nerd Font**.
- **Hyprland**: Unify and centralize font and cursor configurations using dynamic Lua variables in compositor configurations.
- **Backup Utility**: Refactor `backup.sh` to query loaded keys via `ssh-agent` rather than relying on hardcoded private key paths, exclude Lutris runner files, prune deprecated `.localised` exclude pattern, and translate logs from French to English.

### Removed
- **Legacy OS Support**: Drop Ubuntu-specific bootstrap installer script (`dist/ubuntu/install.sh`) and related documentation.
- **Zsh & Utilities**: Remove deprecated `command-not-found` shell plugin and its assets from `.zshrc` and plugin directory.

## [v5.3.0](https://gitlab.com/pad92/dotfiles/-/releases/v5.3.0)

### Added
- **Security & Passwords**: Migrate from 1Password to **Proton Pass** as the default password manager.
- **Security & Passwords**: Add `proton-pass-ssh-agent.service` systemd user service to manage the Proton Pass SSH agent.
- **Security & Passwords**: Add `pass-cli` Zsh autocomplete plugin.
- **Security & Passwords**: Add a centralized SSH agent initialization script (`zsh/init/ssh-agent.zsh`) to automatically detect and export the active SSH socket.
- **Zsh & Utilities**: Add a custom `ssh-copy-agent-keys` function in `zsh/functions/ssh.zsh` to interactively select public keys loaded in the local `ssh-agent` and copy them to a remote server while avoiding duplicates.
- **Neovim & Editors**: Implement a fully modular Lua-based Neovim configuration (`lazy.nvim`, Telescope, Treesitter, Lualine) and add native Wayland support configurations for Antigravity IDE.
- **Hyprland & Display**: Refactor monitor/workspace setups to host-specific modular configurations (`hosts/PadsTower.lua`, `hosts/PadsP5560.lua`), update keybindings, and enable tearing support for low-latency gaming.
- **UWSM & Session Startup**: Integrate UWSM for session management, centralize environment variables, and document systemd startup/GNOME Keyring PAM setup in the Arch Linux install guide.
- **Audio & Services**: Implement a `shelly-notifications` user service, migrate Bluetooth configuration to Wireplumber (`50-bluez-config.conf`), and improve `awww` service reliability with dynamic Wayland socket checks.
- **CI/CD & Docs**: Implement GitHub Actions pipelines for pages deployment/Vim packaging, and add an automated page generator (`gen_pages.py`) with table of contents support.

### Changed
- **Hyprland & Keybindings**: Update applications launcher, keybindings, and window rules to run Proton Pass instead of 1Password.
- **OS Packages**: Update Arch Linux package lists to install Proton Pass CLI instead of 1Password.
- **Gaming & Scripting**: Rewrite `steam-optimize` from Bash to Python 3 (adding JSON parsing, monitor detection, and Forza Horizon 6 overrides), and refactor `awww.sh` wallpaper script with robust error handling and array safety.
- **Modernization & Cleanup**: Clean up `.gitconfig` structure, migrate global VS Code Lua LSP settings to a project-specific `.luarc.json`, and remove `xml2` dependency from `http_crawler.zsh`.
- **Aesthetics & UI**: Update desktop component styling (Waybar, Wofi, Mako, wlogout) to the official **Catppuccin Mocha** palette.

### Removed
- **Legacy Components**: Remove legacy `1password` Zsh plugin, including the helper function `opswd`.
- **Legacy Components**: Remove legacy `~/.xinitrc` configuration and its installer symlink.
- **Legacy Components**: Remove GDM display manager, old `kitty` theme configuration files, legacy helper scripts (`SystemControl.sh`, `power-profiles`, `xrandr.sh`), and the precompiled `greenclip-v4.2` binary.
- **Redundant Configs**: Streamline environments by removing obsolete GNOME Keyring/SSH socket environment variables.

### Fixed
- **Compositor & Display**: Resolve Gamescope mouse containment issues on multi-monitor setups using software rendering (`no_hardware_cursors = true`).
- **Drivers & Stability**: Fix AMD RADV driver stability, refresh rate detection in `steam-optimize`, and correct QT QPA platform separator format compatibility.
- **Sandbox**: Correct Electron feature flags and sandbox configurations.

## [v5.2.1](https://gitlab.com/pad92/dotfiles/-/releases/v5.2.1)

### Changed
- **Status Bar & Packages**: Clean up Waybar configuration by removing unused modules, and consolidate essential package lists (Alacritty, GNOME utilities) into `11_hyprland.txt` and `20_apps.txt`.
- **Documentation**: Update installation guide package paths and README.md to reflect archiving of legacy setups.

### Removed
- **Legacy Configs**: Archive legacy X11, Sway, and Dunst configurations to `.config-archive/`, and prune obsolete package lists, old package diffs, screenshots, and Nitrogen setup instructions.

### Fixed
- **Electron**: Fix Chromium/Chrome electron flags by properly combining multiple `--enable-features` onto a single line.

## [v5.2.0](https://gitlab.com/pad92/dotfiles/-/releases/v5.2.0)

### Added
- **Hyprland Upgrades**: Upgrade Hyprland configuration to 0.55, introduce a centralized configuration module, define standard coding guidelines, and set default workspaces.
- **Gaming & Keybindings**: Add custom Doom (2016) optimizations and Gamescope fixes in `steam-optimize`, and enhance shortcut bindings for screenshots, lock, and session controls.

### Changed
- **Desktop Daemons**: Migrate wallpaper daemon from swww to awww, switch notification system from Dunst to Mako, and refine Hyprland animations/autostart.
- **Refactoring**: Rewrite system backup utility to POSIX shell with improved rsync arguments, and optimize `steam-optimize` with helper functions.

### Fixed
- **Stability**: Resolve fullscreen blackscreen issues and restore Steam overlay functionality.

## [v5.1.1](https://gitlab.com/pad92/dotfiles/-/releases/v5.1.1)

### Added
- **Arch & System**: Add native Gamemode support, integrate firmware updates into the arch upgrade function, and add vimdiff instructions for `.pacnew` files.
- **Hyprland**: Add initial host-specific configuration override support.

### Changed
- **CI & Aliases**: Optimize pre-commit hooks to respect `.editorconfig` settings, enhance pre-commit leak detection, and refine shell alias error checking/validation.
- **Docs & Packages**: Update Arch installation guide with modern practices (archinstall) and refresh the applications package list.

## [v5.1.0](https://gitlab.com/pad92/dotfiles/-/releases/v5.1.0)

### Added
- **Features**: Implement automated changelog generation, add wlogout configuration, expand package manager utilities, and support newer Hyprland features.

### Changed
- **Aesthetics & UI**: Refine Waybar status layouts, keybindings, fonts, system themes, and add missing system fonts.
- **Backup & Editor**: Update VS Code extension lists and configure backup scripts to ignore WebStorage directories.

### Fixed
- **Status & Wallpaper**: Fix temperature display, network formatting, wallpaper rotation rules, and DST-related bugs in status bars.
- **System**: Fix Electron flags and resolve package installation inconsistencies.

## [v5.0.0](https://gitlab.com/pad92/dotfiles/-/releases/v5.0.0)

### Changed
- **Compositor Sync**: Major overhaul and synchronization of Hyprland, Sway, and Waybar configurations.

## [v4.4.1](https://gitlab.com/pad92/dotfiles/-/releases/v4.4.1)

### Changed
- **Themes & Packages**: Update visual themes, system color schemes, and package management helpers.

### Fixed
- **Status Bar**: Correct Waybar temperature readings and network status formatting bugs.

## [v4.4.0](https://gitlab.com/pad92/dotfiles/-/releases/v4.4.0)

### Added
- **Compositor & UI**: Introduce new Hyprland configuration options, add new status bar modules, and enhance package installation scripts.

### Changed
- **Keybinds & Fonts**: Update config files, modernize keyboard shortcuts, and refine typography.

## [v4.3.0](https://gitlab.com/pad92/dotfiles/-/releases/v4.3.0)

### Added
- **Desktop Environments**: Support new Hyprland features, enhance dual i3/Sway configurations, and improve package management wrappers.

### Changed
- **Structure**: Refactor layout organization, update module setups, and simplify the installation flow.

## [v4.2.1](https://gitlab.com/pad92/dotfiles/-/releases/v4.2.1)

### Fixed
- **Stability**: Resolve core stability issues, fix status bar layout bugs, and correct package installation mismatches.

## [v4.2](https://gitlab.com/pad92/dotfiles/-/releases/v4.2)

### Added
- **Structure**: Add new configuration templates, optimize package management systems, and expand documentation.

### Changed
- **Architectural Overhaul**: Restructure file layouts, update system dependencies, and rewrite installer scripts.

## [v4.1](https://gitlab.com/pad92/dotfiles/-/releases/v4.1)

### Added
- **Visuals**: Add new themes, layout configurations, and improve package installation helpers.

### Changed
- **Polish**: Refine keybindings, status bar modules, and enhance overall stability.

## [v4.0](https://gitlab.com/pad92/dotfiles/-/releases/v4.0)

### Added
- **Multi-Compositor**: Complete overhaul of the configuration system, adding initial Hyprland support alongside modernized Sway and i3 setups.

### Changed
- **Architecture**: Redesign file structures and update configurations to support latest upstream software versions.

## [v2.1](https://gitlab.com/pad92/dotfiles/-/releases/v2.1)

### Added
- **Templates**: Add additional package configs, visual themes, and package management helpers.

### Changed
- **Consistency**: Refine status bar layouts, improve installer script reliability, and standardize settings.

## [v2.0](https://gitlab.com/pad92/dotfiles/-/releases/v2.0)

### Added
- **Visuals**: Add window transparency support and initial setup templates.

### Changed
- **Cleanup**: Reorganize system modules, update core keybinds, and clean up initial files.

## [v1.0](https://gitlab.com/pad92/dotfiles/-/releases/v1.0)

### Added
- **Initial Release**: Core Zsh configurations, visual themes, and baseline system utilities.
