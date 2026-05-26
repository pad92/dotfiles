# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Add specific overrides for Forza Horizon 6 in `steam-optimize` ([12ad469](https://gitlab.com/pad92/dotfiles/-/commit/12ad469))
- Integrate UWSM for session start and environment variables ([8819620](https://gitlab.com/pad92/dotfiles/-/commit/8819620), [fe97725](https://gitlab.com/pad92/dotfiles/-/commit/fe97725))
- Update Hyprland keybindings and configuration references ([3c9561f](https://gitlab.com/pad92/dotfiles/-/commit/3c9561f), [b276f51](https://gitlab.com/pad92/dotfiles/-/commit/b276f51))
- Implement automated release workflows and GitLab/GitHub Pages integration ([8a781e2](https://gitlab.com/pad92/dotfiles/-/commit/8a781e2), [ee26a9f](https://gitlab.com/pad92/dotfiles/-/commit/ee26a9f))
- Add GitHub Actions workflow for CI pipeline ([1271fb2](https://gitlab.com/pad92/dotfiles/-/commit/1271fb2))
- Add UWSM Systemd startup and GNOME Keyring PAM setup documentation to Arch Linux installation guide

### Changed
- Update theme, colors, and typography to official Catppuccin Mocha palette and refine overall aesthetics ([3579885](https://gitlab.com/pad92/dotfiles/-/commit/3579885), [a07eb9b](https://gitlab.com/pad92/dotfiles/-/commit/a07eb9b), [4fc7843](https://gitlab.com/pad92/dotfiles/-/commit/4fc7843), [0a92290](https://gitlab.com/pad92/dotfiles/-/commit/0a92290), [ecac0b9](https://gitlab.com/pad92/dotfiles/-/commit/ecac0b9), [7798b53](https://gitlab.com/pad92/dotfiles/-/commit/7798b53))
- Modernize Hyprland autostart using UWSM ([333c239](https://gitlab.com/pad92/dotfiles/-/commit/333c239), [20a9a24](https://gitlab.com/pad92/dotfiles/-/commit/20a9a24))
- Optimize CI/CD pipelines, documentation build process and Pages deployment ([4a27841](https://gitlab.com/pad92/dotfiles/-/commit/4a27841), [7dd08e3](https://gitlab.com/pad92/dotfiles/-/commit/7dd08e3), [b307628](https://gitlab.com/pad92/dotfiles/-/commit/b307628), [931deb5](https://gitlab.com/pad92/dotfiles/-/commit/931deb5), [8cca767](https://gitlab.com/pad92/dotfiles/-/commit/8cca767), [15f832c](https://gitlab.com/pad92/dotfiles/-/commit/15f832c), [fe30ba8](https://gitlab.com/pad92/dotfiles/-/commit/fe30ba8), [f41022b](https://gitlab.com/pad92/dotfiles/-/commit/f41022b), [3a9915a](https://gitlab.com/pad92/dotfiles/-/commit/3a9915a), [2727ee2](https://gitlab.com/pad92/dotfiles/-/commit/2727ee2), [dd1ac7b](https://gitlab.com/pad92/dotfiles/-/commit/dd1ac7b), [9d2eba6](https://gitlab.com/pad92/dotfiles/-/commit/9d2eba6), [0152e05](https://gitlab.com/pad92/dotfiles/-/commit/0152e05))
- Enhance monitor selection and command handling in steam-optimize ([507e071](https://gitlab.com/pad92/dotfiles/-/commit/507e071))
- Update README with editor installation details and Vim config quick links ([8736a1a](https://gitlab.com/pad92/dotfiles/-/commit/8736a1a), [330e5fd](https://gitlab.com/pad92/dotfiles/-/commit/330e5fd))
- Update http_crawler to remove xml2 dependency ([6bbf271](https://gitlab.com/pad92/dotfiles/-/commit/6bbf2711eaf107bb9d0c6e8d613fcec84274f47b))

### Removed
- Remove GDM from the system configuration

## [v5.2.1](https://gitlab.com/pad92/dotfiles/-/releases/v5.2.1)

### Changed
- Cleaned up `waybar` configuration by removing unused modules ([e396f61](https://gitlab.com/pad92/dotfiles/-/commit/e396f61))
- Merged and preserved essential packages (like `alacritty` and GNOME utilities) into `11_hyprland.txt` and `20_apps.txt` ([c965323](https://gitlab.com/pad92/dotfiles/-/commit/c965323))
- Updated `install.md` to fix the package installation path ([c965323](https://gitlab.com/pad92/dotfiles/-/commit/c965323))
- Updated `README.md` to reflect the archiving of legacy environments ([c965323](https://gitlab.com/pad92/dotfiles/-/commit/c965323))

### Removed
- Archived legacy X11, Sway, and Dunst configurations to `.config-archive/` ([c965323](https://gitlab.com/pad92/dotfiles/-/commit/c965323))
- Cleaned up `dist/arch` by removing old package diffs and legacy screenshots ([c965323](https://gitlab.com/pad92/dotfiles/-/commit/c965323))
- Removed obsolete package lists (`10_i3.txt`, `11_sway.txt`, `11_gnome.txt`) ([c965323](https://gitlab.com/pad92/dotfiles/-/commit/c965323))
- Removed legacy Nitrogen configuration from `install.md` ([c965323](https://gitlab.com/pad92/dotfiles/-/commit/c965323))

### Fixed
- Fixed Chromium/Chrome electron flags by properly combining multiple `--enable-features` onto a single line ([6a2de32](https://gitlab.com/pad92/dotfiles/-/commit/6a2de32))

## [v5.2.0](https://gitlab.com/pad92/dotfiles/-/releases/v5.2.0)

### Added
- Update monitor module and consolidate startup notifications ([ef8b516](https://gitlab.com/pad92/dotfiles/-/commit/ef8b516))
- Upgrade Hyprland configuration to 0.55 ([b62490a](https://gitlab.com/pad92/dotfiles/-/commit/b62490a))
- Implement central configuration module for Hyprland ([a6dba06](https://gitlab.com/pad92/dotfiles/-/commit/a6dba06))
- Add standard coding rules and guidelines ([f198f5a](https://gitlab.com/pad92/dotfiles/-/commit/f198f5a))
- Enhance Hyprland keybindings for screenshots, session menu, and lock commands ([c059ed2](https://gitlab.com/pad92/dotfiles/-/commit/c059ed2), [0530cb2](https://gitlab.com/pad92/dotfiles/-/commit/0530cb2), [566d28c](https://gitlab.com/pad92/dotfiles/-/commit/566d28c))
- Add DOOM (2016) optimizations and Gamescope fixes to steam-optimize ([280b982](https://gitlab.com/pad92/dotfiles/-/commit/280b982))
- Set workspace 1 as default monitor ([040cd11](https://gitlab.com/pad92/dotfiles/-/commit/040cd11))

### Changed
- Update monitor configurations ([a806f18](https://gitlab.com/pad92/dotfiles/-/commit/a806f18))
- Add indentation rules for lua files in .editorconfig ([00607a5](https://gitlab.com/pad92/dotfiles/-/commit/00607a5))
- Refactor steam-optimize with helper functions and standard coding rules ([a6142b1](https://gitlab.com/pad92/dotfiles/-/commit/a6142b1), [6ed6765](https://gitlab.com/pad92/dotfiles/-/commit/6ed6765), [78e8421](https://gitlab.com/pad92/dotfiles/-/commit/78e8421), [d29728c](https://gitlab.com/pad92/dotfiles/-/commit/d29728c))
- Optimize backup script by porting to POSIX sh and improving rsync ([4024cfe](https://gitlab.com/pad92/dotfiles/-/commit/4024cfe))
- Switch notification system from dunst to mako ([54a1a7a](https://gitlab.com/pad92/dotfiles/-/commit/54a1a7a))
- Migrate wallpaper daemon from swww to awww ([c1570cc](https://gitlab.com/pad92/dotfiles/-/commit/c1570cc))
- Refine Hyprland animations and autostart configurations ([630eff0](https://gitlab.com/pad92/dotfiles/-/commit/630eff0), [9b995ee](https://gitlab.com/pad92/dotfiles/-/commit/9b995ee), [ce361ea](https://gitlab.com/pad92/dotfiles/-/commit/ce361ea))
- Update README maintenance and maintainer information ([f8f49aa](https://gitlab.com/pad92/dotfiles/-/commit/f8f49aa), [12c5527](https://gitlab.com/pad92/dotfiles/-/commit/12c5527), [9f19255](https://gitlab.com/pad92/dotfiles/-/commit/9f19255))

### Fixed
- Resolve blackscreen issue on fullscreen mode ([ee2bca1](https://gitlab.com/pad92/dotfiles/-/commit/ee2bca1))
- Fix Steam overlay functionality ([54e3093](https://gitlab.com/pad92/dotfiles/-/commit/54e3093))

## [v5.1.1](https://gitlab.com/pad92/dotfiles/-/releases/v5.1.1)

### Added
- Gamemode support ([14104d55](https://gitlab.com/pad92/dotfiles/-/commit/14104d55))
- Firmware update capabilities to arch_update function ([14104d55](https://gitlab.com/pad92/dotfiles/-/commit/14104d55))
- Vimdiff guidance for .pacnew files in clean_arch function ([14104d55](https://gitlab.com/pad92/dotfiles/-/commit/14104d55))
- Hyprland host specific configuration ([14104d55](https://gitlab.com/pad92/dotfiles/-/commit/14104d55))

### Changed
- Optimized pre-commit hooks to better respect .editorconfig settings ([14104d55](https://gitlab.com/pad92/dotfiles/-/commit/14104d55))
- Enhanced security leak detection in pre-commit configuration ([14104d55](https://gitlab.com/pad92/dotfiles/-/commit/14104d55))
- Improved error handling and validation in shell aliases ([14104d55](https://gitlab.com/pad92/dotfiles/-/commit/14104d55))
- Updated arch_update function to include firmware updates ([14104d55](https://gitlab.com/pad92/dotfiles/-/commit/14104d55))
- Updated applications packages list ([14104d55](https://gitlab.com/pad92/dotfiles/-/commit/14104d55))
- Updated Arch Linux installation guide with modern practices and archinstall recommendations ([14104d55](https://gitlab.com/pad92/dotfiles/-/commit/14104d55))
- Enhanced pre-commit configuration with improved leak detection and editorconfig integration ([14104d55](https://gitlab.com/pad92/dotfiles/-/commit/14104d55))
- Expanded .gitignore patterns for comprehensive file exclusion ([14104d55](https://gitlab.com/pad92/dotfiles/-/commit/14104d55))

## [v5.1.0](https://gitlab.com/pad92/dotfiles/-/releases/v5.1.0)

### Added
- Changelog generation functionality ([f78b794](https://gitlab.com/pad92/dotfiles/-/commit/f78b794))
- Wlogout configuration ([8422c78](https://gitlab.com/pad92/dotfiles/-/commit/8422c78))
- New package management features ([2308e30](https://gitlab.com/pad92/dotfiles/-/commit/2308e30))
- Support for newer Hyprland features ([b540b0f](https://gitlab.com/pad92/dotfiles/-/commit/b540b0f))

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
- Waybar temperature display ([11e7a22](https://gitlab.com/pad92/dotfiles/-/commit/11e7a22))
- Resolved network status formatting issues ([6a094de](https://gitlab.com/pad92/dotfiles/-/commit/6a094de))
- Various stability issues ([25f0cad](https://gitlab.com/pad92/dotfiles/-/commit/25f0cad))
- Configuration bugs in status bars ([06a3557](https://gitlab.com/pad92/dotfiles/-/commit/06a3557))
- Package installation inconsistencies ([f8199c6](https://gitlab.com/pad92/dotfiles/-/commit/f8199c6))
- DST-related issues ([4de5dcd](https://gitlab.com/pad92/dotfiles/-/commit/4de5dcd))
- Wallpaper rotation and display issues ([608fd5e](https://gitlab.com/pad92/dotfiles/-/commit/608fd5e))

## [v5.0.0](https://gitlab.com/pad92/dotfiles/-/releases/v5.0.0)

### Changed
- Updated to latest configuration ([8422c78](https://gitlab.com/pad92/dotfiles/-/commit/8422c78))
- Major updates to Hyprland and Sway configurations ([8422c78](https://gitlab.com/pad92/dotfiles/-/commit/8422c78))
- Enhanced Waybar and status bar configurations ([8422c78](https://gitlab.com/pad92/dotfiles/-/commit/8422c78))

## [v4.4.1](https://gitlab.com/pad92/dotfiles/-/releases/v4.4.1)

### Fixed
- Minor issues with configurations ([d5fcda1](https://gitlab.com/pad92/dotfiles/-/commit/d5fcda1))
- Waybar temperature display ([11e7a22](https://gitlab.com/pad92/dotfiles/-/commit/11e7a22))
- Resolved network status formatting issues ([6a094de](https://gitlab.com/pad92/dotfiles/-/commit/6a094de))

### Changed
- Updated themes and color schemes ([0e73433](https://gitlab.com/pad92/dotfiles/-/commit/0e73433))
- Improved package management configurations ([0e73433](https://gitlab.com/pad92/dotfiles/-/commit/0e73433))

## [v4.4.0](https://gitlab.com/pad92/dotfiles/-/releases/v4.4.0)

### Added
- New configuration options for Hyprland ([4bb4afa](https://gitlab.com/pad92/dotfiles/-/commit/4bb4afa))
- Enhanced package installation scripts ([4bb4afa](https://gitlab.com/pad92/dotfiles/-/commit/4bb4afa))
- Additional status bar modules ([4bb4afa](https://gitlab.com/pad92/dotfiles/-/commit/4bb4afa))

### Changed
- Updated to newer versions of configuration files ([4bb4afa](https://gitlab.com/pad92/dotfiles/-/commit/4bb4afa))
- Improved keybinding configurations ([4bb4afa](https://gitlab.com/pad92/dotfiles/-/commit/4bb4afa))
- Updated font settings ([038cb43](https://gitlab.com/pad92/dotfiles/-/commit/038cb43))

## [v4.3.0](https://gitlab.com/pad92/dotfiles/-/releases/v4.3.0)

### Added
- Support for new Hyprland features ([b540b0f](https://gitlab.com/pad92/dotfiles/-/commit/b540b0f))
- Enhanced i3 and Sway configurations ([b540b0f](https://gitlab.com/pad92/dotfiles/-/commit/b540b0f))
- Better package management support ([b540b0f](https://gitlab.com/pad92/dotfiles/-/commit/b540b0f))

### Changed
- Refactored configuration structures ([b540b0f](https://gitlab.com/pad92/dotfiles/-/commit/b540b0f))
- Updated module configurations ([b540b0f](https://gitlab.com/pad92/dotfiles/-/commit/b540b0f))
- Improved installation process ([b540b0f](https://gitlab.com/pad92/dotfiles/-/commit/b540b0f))

## [v4.2.1](https://gitlab.com/pad92/dotfiles/-/releases/v4.2.1)

### Fixed
- Various stability issues ([25f0cad](https://gitlab.com/pad92/dotfiles/-/commit/25f0cad))
- Configuration bugs in status bars ([06a3557](https://gitlab.com/pad92/dotfiles/-/commit/06a3557))
- Package installation inconsistencies ([f8199c6](https://gitlab.com/pad92/dotfiles/-/commit/f8199c6))

## [v4.2](https://gitlab.com/pad92/dotfiles/-/releases/v4.2)

### Added
- New configuration templates ([2308e30](https://gitlab.com/pad92/dotfiles/-/commit/2308e30))
- Enhanced package management capabilities ([2308e30](https://gitlab.com/pad92/dotfiles/-/commit/2308e30))
- Improved documentation ([2308e30](https://gitlab.com/pad92/dotfiles/-/commit/2308e30))

### Changed
- Major restructuring of configuration files ([2308e30](https://gitlab.com/pad92/dotfiles/-/commit/2308e30))
- Updated dependency management ([2308e30](https://gitlab.com/pad92/dotfiles/-/commit/2308e30))
- Improved installation scripts ([2308e30](https://gitlab.com/pad92/dotfiles/-/commit/2308e30))

## [v4.1](https://gitlab.com/pad92/dotfiles/-/releases/v4.1)

### Added
- New themes and visual enhancements ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))
- Additional configuration options ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))
- Improved package installation support ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))

### Changed
- Refined keybinding configurations ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))
- Updated status bar modules ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))
- Improved overall stability ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))

## [v4.0](https://gitlab.com/pad92/dotfiles/-/releases/v4.0)

### Added
- Complete overhaul of configuration system ([f8199c6](https://gitlab.com/pad92/dotfiles/-/commit/f8199c6))
- New Hyprland support ([f8199c6](https://gitlab.com/pad92/dotfiles/-/commit/f8199c6))
- Enhanced Sway configurations ([f8199c6](https://gitlab.com/pad92/dotfiles/-/commit/f8199c6))
- Modernized i3 configurations ([f8199c6](https://gitlab.com/pad92/dotfiles/-/commit/f8199c6))

### Changed
- Major architectural changes ([f8199c6](https://gitlab.com/pad92/dotfiles/-/commit/f8199c6))
- Updated to latest software versions ([f8199c6](https://gitlab.com/pad92/dotfiles/-/commit/f8199c6))
- Restructured file organization ([f8199c6](https://gitlab.com/pad92/dotfiles/-/commit/f8199c6))

## [v2.1](https://gitlab.com/pad92/dotfiles/-/releases/v2.1)

### Added
- Additional configuration files ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))
- Enhanced package management ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))
- New visual themes ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))

### Changed
- Improved configuration consistency ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))
- Updated installation scripts ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))
- Refined status bar layouts ([a62c196](https://gitlab.com/pad92/dotfiles/-/commit/a62c196))

## [v2.0](https://gitlab.com/pad92/dotfiles/-/releases/v2.0)

### Added
- Transparency support ([75a8716](https://gitlab.com/pad92/dotfiles/-/commit/75a8716))
- Cleaned up configurations ([75a8716](https://gitlab.com/pad92/dotfiles/-/commit/75a8716))
- Initial commit improvements ([75a8716](https://gitlab.com/pad92/dotfiles/-/commit/75a8716))

### Changed
- Major cleanup and reorganization ([75a8716](https://gitlab.com/pad92/dotfiles/-/commit/75a8716))
- Updated keybindings ([75a8716](https://gitlab.com/pad92/dotfiles/-/commit/75a8716))
- Improved module configurations ([75a8716](https://gitlab.com/pad92/dotfiles/-/commit/75a8716))

## [v1.0](https://gitlab.com/pad92/dotfiles/-/releases/v1.0)

### Added
- Initial release with Zsh configuration, themes, and utility functions ([8009759](https://gitlab.com/pad92/dotfiles/-/commit/8009759))
