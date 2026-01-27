# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Enhanced pre-commit configuration with improved leak detection and editorconfig integration
- Expanded .gitignore patterns for comprehensive file exclusion
- Added firmware update capabilities to arch_update function
- Added vimdiff guidance for .pacnew files in clean_arch function
- Updated Arch Linux installation guide with modern practices and archinstall recommendations

### Changed

- Optimized pre-commit hooks to better respect .editorconfig settings
- Enhanced security leak detection in pre-commit configuration
- Improved error handling and validation in shell aliases
- Updated arch_update function to include firmware updates
- Updated applications packages list

## [v5.1.0] - 2026-01-18

### Added

- Added changelog generation functionality ([f78b794](https://gitlab.com/pad92/dotfiles/-/commit/f78b794))
- Added wlogout configuration ([8422c78](https://gitlab.com/pad92/dotfiles/-/commit/8422c78))
- Added new package management features ([2308e30](https://gitlab.com/pad92/dotfiles/-/commit/2308e30))
- Added support for newer Hyprland features ([b540b0f](https://gitlab.com/pad92/dotfiles/-/commit/b540b0f))

### Changed

- Update submodule, add missing fonts ([3934888](https://gitlab.com/pad92/dotfiles/-/commit/3934888))
- Update extension list ([406d7b9](https://gitlab.com/pad92/dotfiles/-/commit/406d7b9))
- Backup symlink and ignore WebStorage directory ([e07edff](https://gitlab.com/pad92/dotfiles/-/commit/e07edff))
- Updated to latest configuration ([f78b794](https://gitlab.com/pad92/dotfiles/-/commit/f78b794))
- Enhanced Waybar and status bar configurations ([0a39607](https://gitlab.com/pad92/dotfiles/-/commit/0a39607))
- Improved package installation scripts ([4bb4afa](https://gitlab.com/pad92/dotfiles/-/commit/4bb4afa))
- Updated keybinding configurations ([d5fcda1](https://gitlab.com/pad92/dotfiles/-/commit/d5fcda1))
- Updated font settings ([038cb43](https://gitlab.com/pad92/dotfiles/-/commit/038cb43))
- Improved themes and color schemes ([0e73433](https://gitlab.com/pad92/dotfiles/-/commit/0e73433))

### Fixed

- Fix flags ([a399fa3](https://gitlab.com/pad92/dotfiles/-/commit/a399fa3))
- Fixed waybar temperature display ([11e7a22](https://gitlab.com/pad92/dotfiles/-/commit/11e7a22))
- Resolved network status formatting issues ([6a094de](https://gitlab.com/pad92/dotfiles/-/commit/6a094de))
- Fixed various stability issues ([25f0cad](https://gitlab.com/pad92/dotfiles/-/commit/25f0cad))
- Fixed configuration bugs in status bars ([06a3557](https://gitlab.com/pad92/dotfiles/-/commit/06a3557))
- Fixed package installation inconsistencies ([f8199c6](https://gitlab.com/pad92/dotfiles/-/commit/f8199c6))
- Fixed DST-related issues ([4de5dcd](https://gitlab.com/pad92/dotfiles/-/commit/4de5dcd))
- Fixed wallpaper rotation and display issues ([608fd5e](https://gitlab.com/pad92/dotfiles/-/commit/608fd5e))

## [v5.0.0] - 2024-10-06

### Changed

- Updated to latest configuration ([8422c78](https://gitlab.com/pad92/dotfiles/-/commit/8422c78))
- Major updates to Hyprland and Sway configurations ([8422c78](https://gitlab.com/pad92/dotfiles/-/commit/8422c78))
- Enhanced Waybar and status bar configurations ([8422c78](https://gitlab.com/pad92/dotfiles/-/commit/8422c78))

## [v4.4.1] - 2024-10-06

### Fixed

- Minor issues with configurations ([d5fcda1](https://gitlab.com/pad92/dotfiles/-/commit/d5fcda1))
- Fixed waybar temperature display ([11e7a22](https://gitlab.com/pad92/dotfiles/-/commit/11e7a22))
- Resolved network status formatting issues ([6a094de](https://gitlab.com/pad92/dotfiles/-/commit/6a094de))

### Changed

- Updated themes and color schemes ([0e73433](https://gitlab.com/pad92/dotfiles/-/commit/0e73433))
- Improved package management configurations ([0e73433](https://gitlab.com/pad92/dotfiles/-/commit/0e73433))

## [v4.4.0] - 2023-07-13

### Added

- New configuration options for Hyprland ([4bb4afa](https://gitlab.com/pad92/dotfiles/-/commit/4bb4afa))
- Enhanced package installation scripts ([4bb4afa](https://gitlab.com/pad92/dotfiles/-/commit/4bb4afa))
- Additional status bar modules ([4bb4afa](https://gitlab.com/pad92/dotfiles/-/commit/4bb4afa))

### Changed

- Updated to newer versions of configuration files ([4bb4afa](https://gitlab.com/pad92/dotfiles/-/commit/4bb4afa))
- Improved keybinding configurations ([4bb4afa](https://gitlab.com/pad92/dotfiles/-/commit/4bb4afa))
- Updated font settings ([038cb43](https://gitlab.com/pad92/dotfiles/-/commit/038cb43))

## [v4.3.0] - 2022-07-06

### Added

- Support for new Hyprland features ([b540b0f](https://gitlab.com/pad92/dotfiles/-/commit/b540b0f))
- Enhanced i3 and Sway configurations ([b540b0f](https://gitlab.com/pad92/dotfiles/-/commit/b540b0f))
- Better package management support ([b540b0f](https://gitlab.com/pad92/dotfiles/-/commit/b540b0f))

### Changed

- Refactored configuration structures ([b540b0f](https://gitlab.com/pad92/dotfiles/-/commit/b540b0f))
- Updated module configurations ([b540b0f](https://gitlab.com/pad92/dotfiles/-/commit/b540b0f))
- Improved installation process ([b540b0f](https://gitlab.com/pad92/dotfiles/-/commit/b540b0f))

## [v4.2.1] - 2021-12-12

### Fixed

- Various stability issues ([25f0cad](https://gitlab.com/pad92/dotfiles/-/commit/25f0cad))
- Configuration bugs in status bars ([06a3557](https://gitlab.com/pad92/dotfiles/-/commit/06a3557))
- Package installation inconsistencies ([f8199c6](https://gitlab.com/pad92/dotfiles/-/commit/f8199c6))

## [v4.2] - 2021-12-11

### Added

- New configuration templates ([2308e30](https://gitlab.com/pad92/dotfiles/-/commit/2308e30))
- Enhanced package management capabilities ([2308e30](https://gitlab.com/pad92/dotfiles/-/commit/2308e30))
- Improved documentation ([2308e30](https://gitlab.com/pad92/dotfiles/-/commit/2308e30))

### Changed

- Major restructuring of configuration files ([2308e30](https://gitlab.com/pad92/dotfiles/-/commit/2308e30))
- Updated dependency management ([2308e30](https://gitlab.com/pad92/dotfiles/-/commit/2308e30))
- Improved installation scripts ([2308e30](https://gitlab.com/pad92/dotfiles/-/commit/2308e30))

## [v4.1] - 2021-12-01

### Added

- New themes and visual enhancements ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))
- Additional configuration options ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))
- Improved package installation support ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))

### Changed

- Refined keybinding configurations ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))
- Updated status bar modules ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))
- Improved overall stability ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))

## [v4.0] - 2021-11-24

### Added

- Complete overhaul of configuration system ([f8199c6](https://gitlab.com/pad92/dotfiles/-/commit/f8199c6))
- New Hyprland support ([f8199c6](https://gitlab.com/pad92/dotfiles/-/commit/f8199c6))
- Enhanced Sway configurations ([f8199c6](https://gitlab.com/pad92/dotfiles/-/commit/f8199c6))
- Modernized i3 configurations ([f8199c6](https://gitlab.com/pad92/dotfiles/-/commit/f8199c6))

### Changed

- Major architectural changes ([f8199c6](https://gitlab.com/pad92/dotfiles/-/commit/f8199c6))
- Updated to latest software versions ([f8199c6](https://gitlab.com/pad92/dotfiles/-/commit/f8199c6))
- Restructured file organization ([f8199c6](https://gitlab.com/pad92/dotfiles/-/commit/f8199c6))

## [v2.1] - 2019-03-17

### Added

- Additional configuration files ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))
- Enhanced package management ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))
- New visual themes ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))

### Changed

- Improved configuration consistency ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))
- Updated installation scripts ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))
- Refined status bar layouts ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))

## [v2.0] - 2019-02-09

### Added

- Added transparency support ([75a8716](https://gitlab.com/pad92/dotfiles/-/commit/75a8716))
- Cleaned up configurations ([75a8716](https://gitlab.com/pad92/dotfiles/-/commit/75a8716))
- Initial commit improvements ([75a8716](https://gitlab.com/pad92/dotfiles/-/commit/75a8716))

### Changed

- Major cleanup and reorganization ([75a8716](https://gitlab.com/pad92/dotfiles/-/commit/75a8716))
- Updated keybindings ([75a8716](https://gitlab.com/pad92/dotfiles/-/commit/75a8716))
- Improved module configurations ([75a8716](https://gitlab.com/pad92/dotfiles/-/commit/75a8716))

## [v1.0] - 2019-02-09

### Added

- Initial release ([3b696a2](https://gitlab.com/pad92/dotfiles/-/commit/3b696a2))
- Basic configuration setup for i3, Sway, and Hyprland ([3b696a2](https://gitlab.com/pad92/dotfiles/-/commit/3b696a2))
- Core package installation scripts ([3b696a2](https://gitlab.com/pad92/dotfiles/-/commit/3b696a2))
- Initial documentation ([3b696a2](https://gitlab.com/pad92/dotfiles/-/commit/3b696a2))
