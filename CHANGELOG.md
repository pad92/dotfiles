# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Added documentation for TTY launch and GNOME Keyring session integration in `README.md`

### Removed
- Removed GDM from the system configuration

## [v5.2.1] - 2026-05-21

### Changed
- Cleaned up `waybar` configuration by removing unused modules
- Merged and preserved essential packages (like `alacritty` and GNOME utilities) into `11_hyprland.txt` and `20_apps.txt`
- Updated `install.md` to fix the package installation path
- Updated `README.md` to reflect the archiving of legacy environments

### Removed
- Archived legacy X11, Sway, and Dunst configurations to `.config-archive/`
- Cleaned up `dist/arch` by removing old package diffs and legacy screenshots
- Removed obsolete package lists (`10_i3.txt`, `11_sway.txt`, `11_gnome.txt`)
- Removed legacy Nitrogen configuration from `install.md`

### Fixed
- Fixed Chromium/Chrome electron flags by properly combining multiple `--enable-features` onto a single line

## [v5.2.0] - 2026-05-13

### Added
- Update monitor module and consolidate startup notifications ([ef8b516](/commit/ef8b516))
- Upgrade Hyprland configuration to 0.55 ([b62490a](/commit/b62490a))
- Implement central configuration module for Hyprland ([a6dba06](/commit/a6dba06))
- Add standard coding rules and guidelines ([f198f5a](/commit/f198f5a))
- Enhance Hyprland keybindings for screenshots, session menu, and lock commands ([c059ed2](/commit/c059ed2), [0530cb2](/commit/0530cb2), [566d28c](/commit/566d28c))
- Add DOOM (2016) optimizations and Gamescope fixes to steam-optimize ([280b982](/commit/280b982))
- Set workspace 1 as default monitor ([040cd11](/commit/040cd11))

### Changed
- Update monitor configurations ([a806f18](/commit/a806f18))
- Add indentation rules for lua files in .editorconfig ([00607a5](/commit/00607a5))
- Refactor steam-optimize with helper functions and standard coding rules ([a6142b1](/commit/a6142b1), [6ed6765](/commit/6ed6765), [78e8421](/commit/78e8421), [d29728c](/commit/d29728c))
- Optimize backup script by porting to POSIX sh and improving rsync ([4024cfe](/commit/4024cfe))
- Switch notification system from dunst to mako ([54a1a7a](/commit/54a1a7a))
- Migrate wallpaper daemon from swww to awww ([c1570cc](/commit/c1570cc))
- Refine Hyprland animations and autostart configurations ([630eff0](/commit/630eff0), [9b995ee](/commit/9b995ee), [ce361ea](/commit/ce361ea))
- Update README maintenance and maintainer information ([f8f49aa](/commit/f8f49aa), [12c5527](/commit/12c5527), [9f19255](/commit/9f19255))

### Fixed
- Resolve blackscreen issue on fullscreen mode ([ee2bca1](/commit/ee2bca1))
- Fix Steam overlay functionality ([54e3093](/commit/54e3093))

## [v5.1.1] - 2026-03-01

### Added
- Gamemode support ([14104d55](/commit/14104d55))
- Firmware update capabilities to arch_update function ([14104d55](/commit/14104d55))
- Vimdiff guidance for .pacnew files in clean_arch function ([14104d55](/commit/14104d55))
- Hyprland host specific configuration ([14104d55](/commit/14104d55))

### Changed
- Optimized pre-commit hooks to better respect .editorconfig settings ([14104d55](/commit/14104d55))
- Enhanced security leak detection in pre-commit configuration ([14104d55](/commit/14104d55))
- Improved error handling and validation in shell aliases ([14104d55](/commit/14104d55))
- Updated arch_update function to include firmware updates ([14104d55](/commit/14104d55))
- Updated applications packages list ([14104d55](/commit/14104d55))
- Updated Arch Linux installation guide with modern practices and archinstall recommendations ([14104d55](/commit/14104d55))
- Enhanced pre-commit configuration with improved leak detection and editorconfig integration ([14104d55](/commit/14104d55))
- Expanded .gitignore patterns for comprehensive file exclusion ([14104d55](/commit/14104d55))

## [v5.1.0] - 2026-01-18

### Added
- Changelog generation functionality ([f78b794](/commit/f78b794))
- Wlogout configuration ([8422c78](/commit/8422c78))
- New package management features ([2308e30](/commit/2308e30))
- Support for newer Hyprland features ([b540b0f](/commit/b540b0f))

### Changed
- Update submodule, add missing fonts ([3934888](/commit/3934888))
- Update extension list ([406d7b9](/commit/406d7b9))
- Backup symlink and ignore WebStorage directory ([e07edff](/commit/e07edff))
- Updated to latest configuration ([f78b794](/commit/f78b794))
- Enhanced Waybar and status bar configurations ([0a39607](/commit/0a39607))
- Improved package installation scripts ([4bb4afa](/commit/4bb4afa))
- Updated keybinding configurations ([d5fcda1](/commit/d5fcda1))
- Updated font settings ([038cb43](/commit/038cb43))
- Improved themes and color schemes ([0e73433](/commit/0e73433))

### Fixed
- Fix flags ([a399fa3](/commit/a399fa3))
- Waybar temperature display ([11e7a22](/commit/11e7a22))
- Resolved network status formatting issues ([6a094de](/commit/6a094de))
- Various stability issues ([25f0cad](/commit/25f0cad))
- Configuration bugs in status bars ([06a3557](/commit/06a3557))
- Package installation inconsistencies ([f8199c6](/commit/f8199c6))
- DST-related issues ([4de5dcd](/commit/4de5dcd))
- Wallpaper rotation and display issues ([608fd5e](/commit/608fd5e))

## [v5.0.0] - 2024-10-06

### Changed
- Updated to latest configuration ([8422c78](/commit/8422c78))
- Major updates to Hyprland and Sway configurations ([8422c78](/commit/8422c78))
- Enhanced Waybar and status bar configurations ([8422c78](/commit/8422c78))

## [v4.4.1] - 2024-10-06

### Fixed
- Minor issues with configurations ([d5fcda1](/commit/d5fcda1))
- Waybar temperature display ([11e7a22](/commit/11e7a22))
- Resolved network status formatting issues ([6a094de](/commit/6a094de))

### Changed
- Updated themes and color schemes ([0e73433](/commit/0e73433))
- Improved package management configurations ([0e73433](/commit/0e73433))

## [v4.4.0] - 2023-07-13

### Added
- New configuration options for Hyprland ([4bb4afa](/commit/4bb4afa))
- Enhanced package installation scripts ([4bb4afa](/commit/4bb4afa))
- Additional status bar modules ([4bb4afa](/commit/4bb4afa))

### Changed
- Updated to newer versions of configuration files ([4bb4afa](/commit/4bb4afa))
- Improved keybinding configurations ([4bb4afa](/commit/4bb4afa))
- Updated font settings ([038cb43](/commit/038cb43))

## [v4.3.0] - 2022-07-06

### Added
- Support for new Hyprland features ([b540b0f](/commit/b540b0f))
- Enhanced i3 and Sway configurations ([b540b0f](/commit/b540b0f))
- Better package management support ([b540b0f](/commit/b540b0f))

### Changed
- Refactored configuration structures ([b540b0f](/commit/b540b0f))
- Updated module configurations ([b540b0f](/commit/b540b0f))
- Improved installation process ([b540b0f](/commit/b540b0f))

## [v4.2.1] - 2021-12-12

### Fixed
- Various stability issues ([25f0cad](/commit/25f0cad))
- Configuration bugs in status bars ([06a3557](/commit/06a3557))
- Package installation inconsistencies ([f8199c6](/commit/f8199c6))

## [v4.2] - 2021-12-11

### Added
- New configuration templates ([2308e30](/commit/2308e30))
- Enhanced package management capabilities ([2308e30](/commit/2308e30))
- Improved documentation ([2308e30](/commit/2308e30))

### Changed
- Major restructuring of configuration files ([2308e30](/commit/2308e30))
- Updated dependency management ([2308e30](/commit/2308e30))
- Improved installation scripts ([2308e30](/commit/2308e30))

## [v4.1] - 2021-12-01

### Added
- New themes and visual enhancements ([a62c196](/commit/a62c196))
- Additional configuration options ([a62c196](/commit/a62c196))
- Improved package installation support ([a62c196](/commit/a62c196))

### Changed
- Refined keybinding configurations ([a62c196](/commit/a62c196))
- Updated status bar modules ([a62c196](/commit/a62c196))
- Improved overall stability ([a62c196](/commit/a62c196))

## [v4.0] - 2021-11-24

### Added
- Complete overhaul of configuration system ([f8199c6](/commit/f8199c6))
- New Hyprland support ([f8199c6](/commit/f8199c6))
- Enhanced Sway configurations ([f8199c6](/commit/f8199c6))
- Modernized i3 configurations ([f8199c6](/commit/f8199c6))

### Changed
- Major architectural changes ([f8199c6](/commit/f8199c6))
- Updated to latest software versions ([f8199c6](/commit/f8199c6))
- Restructured file organization ([f8199c6](/commit/f8199c6))

## [v2.1] - 2019-03-17

### Added
- Additional configuration files ([a62c196](/commit/a62c196))
- Enhanced package management ([a62c196](/commit/a62c196))
- New visual themes ([a62c196](/commit/a62c196))

### Changed
- Improved configuration consistency ([a62c196](/commit/a62c196))
- Updated installation scripts ([a62c196](/commit/a62c196))
- Refined status bar layouts ([a62c196](/commit/a62c196))

## [v2.0] - 2019-02-09

### Added
- Transparency support ([75a8716](/commit/75a8716))
- Cleaned up configurations ([75a8716](/commit/75a8716))
- Initial commit improvements ([75a8716](/commit/75a8716))

### Changed
- Major cleanup and reorganization ([75a8716](/commit/75a8716))
- Updated keybindings ([75a8716](/commit/75a8716))
- Improved module configurations ([75a8716](/commit/75a8716))

## [v1.0] - 2019-02-09

### Added
- Initial release ([3b696a2](/commit/3b696a2))
- Basic configuration setup for i3, Sway, and Hyprland ([3b696a2](/commit/3b696a2))
- Core package installation scripts ([3b696a2](/commit/3b696a2))
- Initial documentation ([3b696a2](/commit/3b696a2))
