# Changelog

All notable changes to this project will be documented in this file.

## 🚧 [Unreleased]

### ✨ Added

- **CI / Pages**:
  - Add a sticky navigation menu to every generated documentation page (`gen_pages.py`) linking Home / Changelog / Installation / CI Workflows / GitLab CI, with the current page highlighted and links resolved relatively so the site works under a subpath.
  - Render the documentation pages with their heading emoji/icons intact (`gen_pages.py`) and homogenize the icon style across all docs (README, changelog, install guide, and both CI READMEs).
  - Add `.github/workflows/README.md` documenting the workflows, the shared `.ci_bin/` scripts, and the multi-forge (GitHub/GitLab/Gitea) setup, and publish it to the docs site (mirroring its source path) via `build_pages.sh`.
  - Add `.gitlab/README.md` documenting the GitLab CI pipeline (stages, jobs, the `pages` build-vs-deploy rules, and the shared `.ci_bin/` scripts), and publish it to the docs site (mirroring its source path) via `build_pages.sh`. `build_pages.sh` also writes a `.nojekyll` marker so GitHub Pages serves the dot-directory pages verbatim.
  - Add a **Continuous Integration** section to the main `README.md` summarising the multi-forge (GitHub/GitLab/Gitea) setup and linking to both CI READMEs.
  - Document the variables/secrets in both CI READMEs — all tokens (`GITHUB_TOKEN`, OIDC, `CI_JOB_TOKEN`) are auto-provided, so no manual secrets are required; note the GitHub Pages / Gitea Actions one-time setup prerequisites.
- **Docs**:
  - Add a Hyprland desktop showcase screenshot (`dist/hyprland.webp`) as a hero illustration at the top of `README.md`, and refresh the Neovim feature list (treesitter `main`/Neovim 0.12, LSP `LspAttach` keymaps, gitsigns hunk/blame keymaps).
- **Hyprland**:
  - Add screen zoom on `SUPER + PgUp`/`PgDn` (`Home` resets), driven via `hyprctl eval` + `hl.config` since the Lua parser disables `hyprctl keyword`, with an animated `zoomFactor`. Keyboard binds are used because Hyprland scroll binds leak the scroll event to the focused window ([#9319](https://github.com/hyprwm/Hyprland/issues/9319)).
- **Neovim**:
  - Add `neovim` and `tree-sitter-cli` to the Arch package list (`dist/arch/packages/20_apps.txt`) — `neovim` was missing from the curated lists, and the nvim-treesitter `main` branch compiles parsers through the `tree-sitter` CLI (the `master` branch built them directly with `cc`).
  - Add LSP keymaps via an `LspAttach` autocmd (`lsp.lua`) — `gd`/`gD`/`gi` (definition/declaration/implementation), `<leader>e` (diagnostic float) and `<leader>lf` (format), complementing Neovim 0.11's built-in `grn`/`gra`/`grr`/`K`. The LSP was previously configured but had no bindings.
  - Add gitsigns hunk keymaps via `on_attach` (`editor.lua`) — `]c`/`[c` to navigate hunks, `<leader>gs`/`gr`/`gp`/`gd` to stage/reset/preview/diff, and `<leader>gb` to toggle inline blame.

### ♻️ Changed

- **CI / Pages**:
  - Generate the Pages site in both `deploy-pages.yml` (GitHub) and the `pages` job (GitLab) by calling the reusable `.ci_bin/build_pages.sh` script instead of duplicating the `gen_pages.py` invocations, keeping the page list in a single source of truth. Made `build_pages.sh` POSIX `sh` and git-optional so it runs on minimal CI images (GitLab alpine).
  - Copy static assets referenced by the docs (the `dist/hyprland.webp` README showcase image) into `public/`, mirroring their source path, so relative `src` links resolve on both GitHub Pages and GitLab Pages (`build_pages.sh`).
  - Factor the CHANGELOG release-notes extraction shared by the GitHub and GitLab release jobs into a single POSIX `.ci_bin/extract_release_notes.sh` script, removing the duplicated `sed` logic.
  - Make `release.yml` forge-agnostic — create the release through the REST API (`POST /repos/{owner}/{repo}/releases` via `jq`/`curl`) instead of the `gh` CLI, so the same workflow runs on both GitHub and the Gitea runner (which also scans `.github/workflows`).
  - Guard the GitHub-Pages (`deploy-pages.yml`) and Vim-package (`package-vim.yml`) workflows with `if: github.server_url == 'https://github.com'` so they don't run on the Gitea runner.
  - Theme the documentation-site navbar with the Catppuccin palette (Mantle background, Mauve brand/active link) instead of Bootstrap's default `bg-dark`, and limit heading dividers to `h1`/`h2` to reduce visual clutter.
- **Hyprland**:
  - Output the isolated showcase capture (`bin/hypr-screenshot.sh`) as a web-optimised WebP (lossy, q80 via `WEBP_QUALITY`, max compression effort) instead of PNG — `grim` writes a temporary PNG that is re-encoded with the first available encoder (`cwebp`/`magick`/`convert`/`ffmpeg`).
  - Source the GTK theme name from `hyprtoolkit.conf` (`gtk_theme`) instead of hardcoding `Materia-dark-compact` in `config.lua`, keeping a single source of truth for theming.
  - Adopt physics spring animations for window open/move (`spring` curve `easy`) and align the full animation tree with Hyprland's upstream example, adding dedicated `layers`/`fadeLayers` animations for layer-shell surfaces (launcher, notifications, Waybar) and a `popin` effect on `windowsIn`.
  - Drop the 10-bit `bitdepth` override on the ASUS XG32WCS monitor (PadsTower), reverting to the default depth.
- **Neovim**:
  - Lazy-load Telescope (`cmd = "Telescope"`) and gitsigns (`event = "VeryLazy"`) instead of loading them at startup (`editor.lua`).
  - Move the Treesitter `foldmethod`/`foldexpr` out of the global `options.lua` into the per-filetype `FileType` autocmd in `treesitter.lua`, so folding is only set where a parser is actually started (alongside highlight/indent).
  - Point the Mason dependencies at `mason-org/mason.nvim` and `mason-org/mason-lspconfig.nvim` (the repos moved org), and drop the redundant manual `vim.lsp.enable("lua_ls")` now that mason-lspconfig's `automatic_enable` handles it (`lsp.lua`).
  - Default gitsigns `current_line_blame` to off (toggle via `<leader>gb`) instead of always-on inline blame (`editor.lua`).
  - Translate all configuration comments to English across the `nvim` config.

### 🐛 Fixed

- **Hyprland**:
  - Fix hypridle no longer turning displays off (and waybar workspace scrolling) after the migration to the Lua config: with `hyprland.lua`, `hyprctl dispatch` evaluates its arguments as Lua (`hl.dispatch(...)`), so the legacy `dpms off` / `workspace e+1` syntax failed with a parse error. `hypridle.conf` now dispatches `hl.dsp.dpms("off"/"on")` and `waybar/conf/workspaces.json` uses `hl.dsp.focus({ workspace = "e±1" })`.
- **Installer**:
  - Make Dotbot linking non-destructive for existing `~/.config/*` entries by enabling backups and directory creation instead of forcing removal.
- **CI / Releases**:
  - Fix release-note extraction for changelog headings that include an emoji and release link, and match tag names literally instead of interpolating them into `sed` regexes.
  - Split GitLab Pages validation into a real `build_pages_review` job so non-default branches build docs without using the special `pages` deployment job.
- **Desktop**:
  - Remove forced Hyprland client killing from `wlogout` reboot/shutdown/logout actions to avoid bypassing application save prompts.
  - Store Hyprlock MPRIS artwork under the user runtime directory instead of fixed `/tmp` paths.
  - Add the missing Waybar `headsetcontrol` helper referenced by the audio module.
- **Docs & Shell**:
  - Fix the Vim-only bootstrap command to pipe into `bash`, and remove shebangs from sourced/non-executable shell files so pre-commit executable checks pass.
  - Guard `uwsm` startup in `.zshrc` and avoid running `tty` from `.zshenv` for non-interactive shells.
- **CI / Pages**:
  - Fix fenced code blocks nested inside list items rendering as a plain paragraph (e.g. the `git clone … ./install` install snippet leaking `:::sh`) — `gen_pages.py` now extracts every fenced block, dedents it, and renders it with Pygments before Markdown conversion, so in-list code blocks display correctly with highlighting.
  - Add the Pygments syntax-highlighting colour theme (`dracula`, scoped to `.codehilite`) to the generated stylesheet — code blocks were emitting token spans with no matching CSS, so they rendered monochrome.
  - Fix the custom table-of-contents styling never applying: the rules targeted `nav[data-toggle='toc']` but the element is `<nav id="toc">`, so they are now keyed on `#toc`.
  - Keep the sticky table of contents below the navbar (offset + higher navbar `z-index`) so it no longer slides over the menu when scrolling.
  - Fix the 404 on the CI Workflows page on GitHub Pages — `actions/upload-pages-artifact` strips `.git`/`.github` from the deployed tarball, so the page generated under `public/.github/workflows/README.md/` was never published. It is now published under `public/github/workflows/README.md/` (leading dot dropped), with the site nav (`gen_pages.py`) and README updated to match.
- **Docs**:
  - Annotate the code fences in `dist/arch/install.md` with languages (`sh`, `text`, `ini`) so they get syntax highlighting, and wrap the previously unfenced shell snippet in the Sound section in a fenced block.
- **Neovim**:
  - Fix the treesitter highlighter crashing on Markdown (`README.md`) under Neovim 0.12 — `Decoration provider "start" … attempt to call method 'range' (a nil value)`. The pinned nvim-treesitter `master` branch is frozen at Neovim 0.10/0.11 support; migrate `treesitter.lua` to the `main` branch (`require('nvim-treesitter').install()` + `vim.treesitter.start()` via a `FileType` autocmd) which supports Neovim 0.12, restoring Markdown highlighting.

## 🏷️ [v5.4.0](https://gitlab.com/pad92/dotfiles/-/releases/v5.4.0)

### ✨ Added

- **CI / Pages**:
  - Add a `post-commit` hook (via `pre-commit`) that regenerates the local `public/` documentation preview after each commit, backed by a reusable `.ci_bin/build_pages.sh` script also usable in CI.

### ♻️ Changed

- **Hyprland**:
  - Increase animation speeds for windows, borders, fades, and workspaces for snappier UI transitions, and remove unused `borderangle` animation.
  - Tone down blur and shadow effects — reduce blur passes, disable opacity ignore and xray, and lower shadow range and render power.
  - Cap ASUS XG32WCS monitor at 60 Hz for productivity use on PadsP5560.
  - Remove hardware cursor override from PadsP5560 host config (use global default).
  - Simplify window rules — remove legacy KeePassXC, Bitwarden, and Dolphin rules, keep only Proton Pass for password manager.
  - Trim blur layer rules to `logout_dialog` only, removing unused swaync entries.
  - Launch `hyprlauncher` in daemon mode (`-d`) at autostart for instant toggle via keybind.
  - Simplify Lua configuration — merge `layout.lua` into `appearance.lua`, inline `utils.lua` helpers, delete empty `workspaces.lua`, and remove verbose comment banners across all files (~75% noise reduction).
  - Simplify the logout command to `pkill wlogout || wlogout` by removing the dead Quickshell (`qs`/`$qsConfig`) branch, since Quickshell is not installed.
  - Remove the redundant `SUPER+SHIFT+F` float-toggle binding (kept on `SUPER+ALT+Space`).
- **Hyprlock**:
  - Reduce playerctl widget update frequency from 1s/2s to 3s/5s to lower lock screen resource usage.
- **PipeWire**:
  - Enable WebRTC voice activity detection (VAD) and lazy activation (`node.passive`) on echo-cancel module to reduce CPU usage when mic is idle.
  - Compact voice effects configuration, removing redundant comments and whitespace.
- **Waybar**:
  - Split config into per-host files (`config.PadsTower`, `config.PadsP5560`) — desktop omits battery, backlight, and Intel temperature modules.
  - Remove unused weather module (`custom/weather`) configuration.
  - Remove dead `#custom-spotify`/`#custom-weather` CSS selectors.
- **Alacritty**:
  - Vendor the single in-use `base16-material-darker-256` theme under `themes/` and drop the 2 MB `base16-alacritty` submodule.
- **GTK**:
  - Fix `gtk-application-prefer-dark-theme` to `true`, align icon theme to `Papirus-Dark` and cursor to `Adwaita` to match Hyprland settings.
  - Remove stale Breeze Light `colors.css` that conflicted with the dark theme.
- **Systemd**:
  - Remove redundant `awww.service` enablement in `default.target.wants` (already in `graphical-session.target.wants`).
  - Change wallpaper rotation interval from 15 minutes to 30 minutes.
- **Installer**:
  - Add automatic hostname-based Waybar config symlink creation in `install.conf.yaml`.
  - Restore the terminal cursor on exit in the AUR-helper bootstrap (`trap '… show_cursor' EXIT`) and drop the obsolete `xrdb`/`.Xresources` reload step from `apply_live_changes`.
- **XDG**:
  - Move `xdg-dirs/` files to standard `.config/` root location for `xdg-user-dirs-update` compatibility.
- **Zsh**:
  - Cache the `compinit` dump and only rebuild it (with the security audit) once a day, reusing it with `-C` otherwise to speed up shell startup; remove a duplicate `single-ignored` completion zstyle.
- **Scripts**:
  - Modernize the empty-argument test in `diff-cmd` (`[ -z "$3" ]`) and remove a dead `meld` comment line.
- **CI / Pages**:
  - Simplify the CSS-path logic in `gen_pages.py` by removing redundant `public/`-prefixed branches that duplicated the generic depth-based formula.
  - Make the generated documentation pages responsive — wide tables now scroll horizontally on small screens instead of overflowing the layout, with adapted heading sizes and container padding on mobile; widen the main content block to the standard Bootstrap `1140px` container; remove a stray non-project comment block from `style.css`.
  - Minify the generated HTML and the copied `style.css` in `gen_pages.py` — collapse inter-tag whitespace (preserving `<pre>`/`<code>`/`<script>` content) and strip CSS comments/whitespace (~36% smaller CSS); drop the now-unused `shutil` import.

### 🗑️ Removed

- **neofetch**:
  - Remove deprecated neofetch configuration (743 lines) — replaced by fastfetch.
- **ashell**, **noctalia**:
  - Remove empty unused configuration directories.
- **Alacritty**:
  - Remove stale base16 auto-backup file.
- **Submodules**:
  - Prune five stale `.gitmodules` entries left over from the i3/X11 era — `zsh-notify`, `i3blocks-contrib`, `i3spotifystatus`, `gruvbox-rofi`, and `base16-alacritty`.
- **X11**:
  - Remove vestigial `.Xresources` and `.screenrc` (byobu/screen) leftovers on the all-Wayland setup.
- **Hyprland**:
  - Remove the orphan `hyprpaper.conf` (wallpapers are handled by `awww`).
- **Waybar**:
  - Remove three unused module scripts (`modules/headsetcontrol`, `modules/spotify`, `modules/mediaplayer.py`) — `headsetcontrol` is superseded by the inline `exec` in `audio.json`.
  - Remove the unused `network` module config from `conf/network.json` and its CSS — it duplicated the `nm-applet` tray indicator.

## 🏷️ [v5.3.2](https://gitlab.com/pad92/dotfiles/-/releases/v5.3.2)

### ✨ Added

- **Hyprland**:
  - Add `hyprlauncher` support as the primary desktop application launcher and clipboard history picker.
  - Add modular helper scripts in `.config/hypr/include/` to encapsulate configuration loading (`toolkit.lua`), host configuration loading (`host.lua`), and core layout/utility helpers (`utils.lua`).
- **Theming**:
  - Add `hyprtoolkit.conf` to configure global `hyprtoolkit` aesthetics matching the Gruvbox colorscheme (using `0xAARRGGBB` hex color format).
- **Neovim**:
  - Add StyLua configuration file `stylua.toml` to support local code validation.
- **Alacritty**:
  - Add `Shift+Return` keyboard binding to send escape sequence for improved terminal compatibility.
- **yay**:
  - Add Lua-based configuration system with automated AUR safety hooks, including validation checks for suspicious PKGBUILD patterns, orphan packages, and maintainer changes.
  - Add update cooldown hook to automatically defer upgrading packages updated less than 48 hours ago.

### ♻️ Changed

- **Hyprland**:
  - Refactor Lua configurations to dynamically parse and source appearance, typography, and color settings from `hyprtoolkit.conf` with automatic hex format translation and fallbacks.
  - Modularize and factorize main entrypoint and component sub-configurations (`.config/hypr/conf/input.lua`, `.config/hypr/conf/layout.lua`, `.config/hypr/conf/appearance.lua`) to eliminate duplicate config parameters and structural redundancy.
  - Optimize workspace bindings in `.config/hypr/conf/keybindings.lua` by lifting hardware keycode allocations out of loops and extending support to a 10th workspace mapped to key `0` and numpad `0`.
  - Guard device-specific input overrides to only apply when a device name is configured, and remove hardcoded placeholder device entry.
  - Fix fullscreen keybinding syntax and remove stale Rofi references from window rules and blur layers.
  - Fix `hypridle` DPMS commands to use proper `hyprctl dispatch dpms on/off` syntax instead of invalid Lua dispatch calls.
  - Fix typos in `hyprlock` comment and `playerctlock.sh` messages and usage output.
- **Neovim**:
  - Migrate from deprecated `vim.loop` to `vim.uv` API, consolidate backup/writebackup options removing redundant swap directory setup, and change `nvim-cmp` confirm behavior to not auto-select the first completion item.
- **Waybar**:
  - Remove legacy Sway workspace, mode, and taskbar module definitions from configuration; retain Hyprland-only modules.
  - Fix `spotify` module string comparison, variable quoting, icon, and JSON output (now uses `jq`); fix `headsetcontrol` shebang to `bash`.
- **Zsh**:
  - Harden `.zshrc` with proper variable quoting, remove duplicate `compinit` call, remove bash-specific `HISTCONTROL`/`HISTIGNORE` variables, and fix `fastfetch` detection using `command -v`.
  - Refactor and simplify system update function in `arch.zsh` to improve error handling and command checks.
- **Electron**:
  - Remove redundant `--ozone-platform-hint=auto` flag from Chrome/Electron configuration, keeping explicit `--ozone-platform=wayland`.
- **Backup Utility**:
  - Switch shebang to `bash`, use `$XDG_RUNTIME_DIR` for SSH control socket, and change `yay -Scc` to `yay -Sc` to preserve non-package caches.
- **Scripts**:
  - Fix shell quoting and test syntax in `comcut`, replace `eval` with safer `bash -c` in `diff-cmd`, and simplify DPI logic in `razer_dpi.py`.
- **Steam-Optimize**:
  - Add signal handling (`SIGTERM`/`SIGHUP`) and `atexit` cleanup for robust session teardown, propagate game exit code, track mouse DPI changes, add `gamescope`/`game-performance` availability checks, factor shared Forza Horizon profile, defer DND activation until after startup, create `.bak` backups before writing VDF configs, and specify `utf-8` encoding on all file operations.
- **Installer**:
  - Refactor `install` script for improved reliability, safer path expansion, headless TTY checking, and optimized package installation caching.

### 🗑️ Removed

- **Wofi**:
  - Clean up and remove all wofi configuration files (`.config/wofi`) and package installer entries.
- **Kanshi**:
  - Remove legacy Sway/Kanshi monitor profile configuration (`.config/kanshi/config`).
- **Systemd**:
  - Remove legacy X11 `xautolock.service` unit file.
- **Wlogout**:
  - Remove unused icon assets (`hibernate-hover1.png`, `moon_865813.png`, `sleep2.png`).

## 🏷️ [v5.3.1](https://gitlab.com/pad92/dotfiles/-/releases/v5.3.1)

### ✨ Added

- **Backup Utility**:
  - Introduce remote disk space delta calculation and log file size changes upon backup completion.
- **Installer**:
  - Add post-installation hook (`apply_live_changes`) to dynamically rebuild font cache, reload X resources (`xrdb`), and refresh desktop environments (Mako, Waybar).

### ♻️ Changed

- **System Fonts**:
  - Standardize system-wide body and desktop environment UI fonts (GTK, Hyprland, Mako, wlogout, wofi) to **DejaVu Sans** and terminal/code blocks to **JetBrainsMono Nerd Font**.
- **Hyprland**:
  - Unify and centralize font and cursor configurations using dynamic Lua variables in compositor configurations.
- **Backup Utility**:
  - Refactor `backup.sh` to query loaded keys via `ssh-agent` rather than relying on hardcoded private key paths, exclude Lutris runner files, prune deprecated `.localised` exclude pattern, and translate logs from French to English.

### 🗑️ Removed

- **Legacy OS Support**:
  - Drop Ubuntu-specific bootstrap installer script (`dist/ubuntu/install.sh`) and related documentation.
- **Zsh & Utilities**:
  - Remove deprecated `command-not-found` shell plugin and its assets from `.zshrc` and plugin directory.

## 🏷️ [v5.3.0](https://gitlab.com/pad92/dotfiles/-/releases/v5.3.0)

### ✨ Added

- **Security & Passwords**:
  - Migrate from 1Password to **Proton Pass** as the default password manager.
  - Add `proton-pass-ssh-agent.service` systemd user service to manage the Proton Pass SSH agent.
  - Add `pass-cli` Zsh autocomplete plugin.
  - Add a centralized SSH agent initialization script (`zsh/init/ssh-agent.zsh`) to automatically detect and export the active SSH socket.
- **Zsh & Utilities**:
  - Add a custom `ssh-copy-agent-keys` function in `zsh/functions/ssh.zsh` to interactively select public keys loaded in the local `ssh-agent` and copy them to a remote server while avoiding duplicates.
- **Neovim & Editors**:
  - Implement a fully modular Lua-based Neovim configuration (`lazy.nvim`, Telescope, Treesitter, Lualine) and add native Wayland support configurations for Antigravity IDE.
- **Hyprland & Display**:
  - Refactor monitor/workspace setups to host-specific modular configurations (`hosts/PadsTower.lua`, `hosts/PadsP5560.lua`), update keybindings, and enable tearing support for low-latency gaming.
- **UWSM & Session Startup**:
  - Integrate UWSM for session management, centralize environment variables, and document systemd startup/GNOME Keyring PAM setup in the Arch Linux install guide.
- **Audio & Services**:
  - Implement a `shelly-notifications` user service, migrate Bluetooth configuration to Wireplumber (`50-bluez-config.conf`), and improve `awww` service reliability with dynamic Wayland socket checks.
- **CI/CD & Docs**:
  - Implement GitHub Actions pipelines for pages deployment/Vim packaging, and add an automated page generator (`gen_pages.py`) with table of contents support.

### ♻️ Changed

- **Hyprland & Keybindings**:
  - Update applications launcher, keybindings, and window rules to run Proton Pass instead of 1Password.
- **OS Packages**:
  - Update Arch Linux package lists to install Proton Pass CLI instead of 1Password.
- **Gaming & Scripting**:
  - Rewrite `steam-optimize` from Bash to Python 3 (adding JSON parsing, monitor detection, and Forza Horizon 6 overrides), and refactor `awww.sh` wallpaper script with robust error handling and array safety.
- **Modernization & Cleanup**:
  - Clean up `.gitconfig` structure, migrate global VS Code Lua LSP settings to a project-specific `.luarc.json`, and remove `xml2` dependency from `http_crawler.zsh`.
- **Aesthetics & UI**:
  - Update desktop component styling (Waybar, Wofi, Mako, wlogout) to the official **Catppuccin Mocha** palette.

### 🗑️ Removed

- **Legacy Components**:
  - Remove legacy `1password` Zsh plugin, including the helper function `opswd`.
  - Remove legacy `~/.xinitrc` configuration and its installer symlink.
  - Remove GDM display manager, old `kitty` theme configuration files, legacy helper scripts (`SystemControl.sh`, `power-profiles`, `xrandr.sh`), and the precompiled `greenclip-v4.2` binary.
- **Redundant Configs**:
  - Streamline environments by removing obsolete GNOME Keyring/SSH socket environment variables.

### 🐛 Fixed

- **Compositor & Display**:
  - Resolve Gamescope mouse containment issues on multi-monitor setups using software rendering (`no_hardware_cursors = true`).
- **Drivers & Stability**:
  - Fix AMD RADV driver stability, refresh rate detection in `steam-optimize`, and correct QT QPA platform separator format compatibility.
- **Sandbox**:
  - Correct Electron feature flags and sandbox configurations.

## 🏷️ [v5.2.1](https://gitlab.com/pad92/dotfiles/-/releases/v5.2.1)

### ♻️ Changed

- **Status Bar & Packages**:
  - Clean up Waybar configuration by removing unused modules, and consolidate essential package lists (Alacritty, GNOME utilities) into `11_hyprland.txt` and `20_apps.txt`.
- **Documentation**:
  - Update installation guide package paths and README.md to reflect archiving of legacy setups.

### 🗑️ Removed

- **Legacy Configs**:
  - Archive legacy X11, Sway, and Dunst configurations to `.config-archive/`, and prune obsolete package lists, old package diffs, screenshots, and Nitrogen setup instructions.

### 🐛 Fixed

- **Electron**:
  - Fix Chromium/Chrome electron flags by properly combining multiple `--enable-features` onto a single line.

## 🏷️ [v5.2.0](https://gitlab.com/pad92/dotfiles/-/releases/v5.2.0)

### ✨ Added

- **Hyprland Upgrades**:
  - Upgrade Hyprland configuration to 0.55, introduce a centralized configuration module, define standard coding guidelines, and set default workspaces.
- **Gaming & Keybindings**:
  - Add custom Doom (2016) optimizations and Gamescope fixes in `steam-optimize`, and enhance shortcut bindings for screenshots, lock, and session controls.

### ♻️ Changed

- **Desktop Daemons**:
  - Migrate wallpaper daemon from swww to awww, switch notification system from Dunst to Mako, and refine Hyprland animations/autostart.
- **Refactoring**:
  - Rewrite system backup utility to POSIX shell with improved rsync arguments, and optimize `steam-optimize` with helper functions.

### 🐛 Fixed

- **Stability**:
  - Resolve fullscreen blackscreen issues and restore Steam overlay functionality.

## 🏷️ [v5.1.1](https://gitlab.com/pad92/dotfiles/-/releases/v5.1.1)

### ✨ Added

- **Arch & System**:
  - Add native Gamemode support, integrate firmware updates into the arch upgrade function, and add vimdiff instructions for `.pacnew` files.
- **Hyprland**:
  - Add initial host-specific configuration override support.

### ♻️ Changed

- **CI & Aliases**:
  - Optimize pre-commit hooks to respect `.editorconfig` settings, enhance pre-commit leak detection, and refine shell alias error checking/validation.
- **Docs & Packages**:
  - Update Arch installation guide with modern practices (archinstall) and refresh the applications package list.

## 🏷️ [v5.1.0](https://gitlab.com/pad92/dotfiles/-/releases/v5.1.0)

### ✨ Added

- **Features**:
  - Implement automated changelog generation, add wlogout configuration, expand package manager utilities, and support newer Hyprland features.

### ♻️ Changed

- **Aesthetics & UI**:
  - Refine Waybar status layouts, keybindings, fonts, system themes, and add missing system fonts.
- **Backup & Editor**:
  - Update VS Code extension lists and configure backup scripts to ignore WebStorage directories.

### 🐛 Fixed

- **Status & Wallpaper**:
  - Fix temperature display, network formatting, wallpaper rotation rules, and DST-related bugs in status bars.
- **System**:
  - Fix Electron flags and resolve package installation inconsistencies.

## 🏷️ [v5.0.0](https://gitlab.com/pad92/dotfiles/-/releases/v5.0.0)

### ♻️ Changed

- **Compositor Sync**:
  - Major overhaul and synchronization of Hyprland, Sway, and Waybar configurations.

## 🏷️ [v4.4.1](https://gitlab.com/pad92/dotfiles/-/releases/v4.4.1)

### ♻️ Changed

- **Themes & Packages**:
  - Update visual themes, system color schemes, and package management helpers.

### 🐛 Fixed

- **Status Bar**:
  - Correct Waybar temperature readings and network status formatting bugs.

## 🏷️ [v4.4.0](https://gitlab.com/pad92/dotfiles/-/releases/v4.4.0)

### ✨ Added

- **Compositor & UI**:
  - Introduce new Hyprland configuration options, add new status bar modules, and enhance package installation scripts.

### ♻️ Changed

- **Keybinds & Fonts**:
  - Update config files, modernize keyboard shortcuts, and refine typography.

## 🏷️ [v4.3.0](https://gitlab.com/pad92/dotfiles/-/releases/v4.3.0)

### ✨ Added

- **Desktop Environments**:
  - Support new Hyprland features, enhance dual i3/Sway configurations, and improve package management wrappers.

### ♻️ Changed

- **Structure**:
  - Refactor layout organization, update module setups, and simplify the installation flow.

## 🏷️ [v4.2.1](https://gitlab.com/pad92/dotfiles/-/releases/v4.2.1)

### 🐛 Fixed

- **Stability**:
  - Resolve core stability issues, fix status bar layout bugs, and correct package installation mismatches.

## 🏷️ [v4.2](https://gitlab.com/pad92/dotfiles/-/releases/v4.2)

### ✨ Added

- **Structure**:
  - Add new configuration templates, optimize package management systems, and expand documentation.

### ♻️ Changed

- **Architectural Overhaul**:
  - Restructure file layouts, update system dependencies, and rewrite installer scripts.

## 🏷️ [v4.1](https://gitlab.com/pad92/dotfiles/-/releases/v4.1)

### ✨ Added

- **Visuals**:
  - Add new themes, layout configurations, and improve package installation helpers.

### ♻️ Changed

- **Polish**:
  - Refine keybindings, status bar modules, and enhance overall stability.

## 🏷️ [v4.0](https://gitlab.com/pad92/dotfiles/-/releases/v4.0)

### ✨ Added

- **Multi-Compositor**:
  - Complete overhaul of the configuration system, adding initial Hyprland support alongside modernized Sway and i3 setups.

### ♻️ Changed

- **Architecture**:
  - Redesign file structures and update configurations to support latest upstream software versions.

## 🏷️ [v2.1](https://gitlab.com/pad92/dotfiles/-/releases/v2.1)

### ✨ Added

- **Templates**:
  - Add additional package configs, visual themes, and package management helpers.

### ♻️ Changed

- **Consistency**:
  - Refine status bar layouts, improve installer script reliability, and standardize settings.

## 🏷️ [v2.0](https://gitlab.com/pad92/dotfiles/-/releases/v2.0)

### ✨ Added

- **Visuals**:
  - Add window transparency support and initial setup templates.

### ♻️ Changed

- **Cleanup**:
  - Reorganize system modules, update core keybinds, and clean up initial files.

## 🏷️ [v1.0](https://gitlab.com/pad92/dotfiles/-/releases/v1.0)

### ✨ Added

- **Initial Release**:
  - Core Zsh configurations, visual themes, and baseline system utilities.
