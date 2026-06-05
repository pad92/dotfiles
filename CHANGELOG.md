# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **Zsh & Utilities**: Add a custom `ssh-copy-agent-keys` function in `zsh/functions/ssh.zsh` to interactively select public keys loaded in the local `ssh-agent` and copy them to a remote server while avoiding duplicates.
- **Neovim & Editors**: Implement a fully modular Lua-based Neovim configuration (`lazy.nvim`, Telescope, Treesitter, Lualine) and add native Wayland support configurations for Antigravity IDE.
- **Hyprland & Display**: Refactor monitor/workspace setups to host-specific modular configurations (`hosts/PadsTower.lua`, `hosts/PadsP5560.lua`), update keybindings, and enable tearing support for low-latency gaming.
- **UWSM & Session Startup**: Integrate UWSM for session management, centralize environment variables, and document systemd startup/GNOME Keyring PAM setup in the Arch Linux install guide.
- **Audio & Services**: Implement a `shelly-notifications` user service, migrate Bluetooth configuration to Wireplumber (`50-bluez-config.conf`), and improve `awww` service reliability with dynamic Wayland socket checks.
- **CI/CD & Docs**: Implement GitHub Actions pipelines for pages deployment/Vim packaging, and add an automated page generator (`gen_pages.py`) with table of contents support.

### Changed
- **Gaming & Scripting**: Rewrite `steam-optimize` from Bash to Python 3 (adding JSON parsing, monitor detection, and Forza Horizon 6 overrides), and refactor `awww.sh` wallpaper script with robust error handling and array safety.
- **Modernization & Cleanup**: Clean up `.gitconfig` structure, migrate global VS Code Lua LSP settings to a project-specific `.luarc.json`, and remove `xml2` dependency from `http_crawler.zsh`.
- **Aesthetics & UI**: Update desktop component styling (Waybar, Wofi, Mako, wlogout) to the official **Catppuccin Mocha** palette.

### Removed
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
