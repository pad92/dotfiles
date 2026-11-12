# Changelog

Release history and changes planned for the next version.

## [Unreleased]

### Added

- **Zsh**:
  - Complete the commands that only ship a bash completion (`wg`,
    `wg-quick`, `fdisk`, `flock`, `taskset`, `virt-install`, `mkfs`, ...)
    through `bashcompinit`. The bash file is sourced on the first TAB. Files
    that need the bash-completion helpers or load only in bash are skipped,
    and a bash function that offers nothing falls back to file names.
  - Complete `sops` and `git-lfs` from the script each tool generates, cached
    in `~/.zcache/generated` until the tool is updated. Arch's `_sops` starts
    with a blank line, so compinit skips it, and `_git-lfs` is empty.
- **Hyprland**:
  - Add screen recording with `hypr-record.sh` and wf-recorder. `CTRL + Print`
    records a window or a region and `CTRL + SHIFT + Print` the focused screen;
    the same key stops it. The file is a small H.264 MP4 in
    `~/Videos/Recordings`, and a failed recording keeps its `.mp4.part` file
    instead of being renamed. Frames are copied continuously (`wf-recorder -D`):
    with damage tracking, a still screen gave an unreadable MP4 and a stop
    waited for the next screen update.
  - Add a Waybar `REC` indicator that stops the recording when clicked.
  - Install `wf-recorder` with the Hyprland package group (Arch and Fedora).
  - `SUPER + F1` opens a searchable Hyprlauncher list of the keybindings
    Hyprland has loaded (`hypr-keybinds.sh`, read from `hyprctl binds -j`).
    A bind without a description is listed under its dispatcher name.
  - Every bind in `keybindings.lua` now has a description, and
    `tests/hypr-keybinds.sh` fails when a new one is added without one.
- **OBS**:
  - Add the `22_obs` package group and the `make install-obs` profile, which
    installs OBS, its PipeWire and portal runtime and the detected GPU drivers
    without the rest of the workstation.
  - Add the `obs` role: encoder, canvas, frame rate and webcam come from the
    host, with a test encode before a hardware encoder is used. It creates the
    profiles and scene collections once and leaves them to OBS.
  - Create an "Enregistrement" profile, which records the native canvas at
    constant quality, and a "Streaming" profile, which streams 1080p at a
    constant bitrate and records with the stream encoder.
  - Configure v4l2loopback with `exclusive_caps=1` so web meetings such as
    Teams can use the OBS virtual camera. A Firefox policy makes Firefox read
    V4L2 cameras directly, since PipeWire never lists the loopback device.
  - Cut the person out of the webcam background with obs-backgroundremoval
    (Robust Video Matting on the CPU, whose soft alpha follows hair; the
    lighter MediaPipe model remains available with `obs_webcam_model`). A soft
    blur remains available with `obs_webcam_background=blur`.
  - Warn when no webcam is found. The scenes are written once, so a camera
    plugged in later never reached them and only `webcam: none` in the final
    report said so.
  - Create one scene collection per palette: "Applis - Sombre" and
    "Applis - Clair" follow the brand guide (#41A890 accent), "Applis -
    Gruvbox" matches the desktop theme. Titles use static Montserrat weights.
  - Install the running kernel's headers when a DKMS package is selected.
  - Partial profiles such as `make install-obs` add their groups to the saved
    package selection instead of replacing it (`packages_state_merge_selection`).
- **DNS**:
  - Add the `dns` tag, which makes systemd-resolved the only resolver: LLMNR
    off, mDNS for resolving only, and no compiled-in public fallback servers.
    `system_dns_manage: false` leaves the resolver alone.
  - Add a migration note for hosts installed with openresolv and the dnsmasq
    relay (`dist/arch/dns-migration.md`): preview, apply, checks, undo, and
    package removal.
- **VPN**:
  - Add the `23_vpn` package group (`openfortivpn`), selected on PadsP5560
    only, and the `vpn` tag of the `system` role. The VPN uses the browser
    SAML login and gives its DNS servers to systemd-resolved on the ppp link,
    so `/etc/resolv.conf` stays the resolved stub link.
  - The gateway lives only in the Ansible Vault
    (`ansible/group_vars/all/vault_vpn.yml`, ignored by Git). Without it the
    role changes nothing. Values are checked before they reach the daemon
    configuration or the polkit rule.
  - A polkit rule lets the session user start and stop
    `openfortivpn@work.service`, and only that unit, without a password.
  - Add a Waybar `VPN` indicator: a click connects and opens the SAML login
    in the browser, a second click disconnects.
- **Ansible Vault**:
  - Add `vault-toggle`, which encrypts a plain file or decrypts an encrypted
    one in place. It reads the password from the Ansible environment or
    `ansible.cfg`, else from the nearest `.vault` file above the target, and
    refuses to decrypt a file that Git would commit.
  - Add a Zed task and the `CTRL + ALT + V` binding that run it on the active
    file. The playbook now manages `~/.config/zed/tasks.json` and
    `keymap.json`.
  - Install Zed on Arch with the `10_sre_devops` package group.
- **AI coding agents**:
  - The Claude Code status line shows the tokens in the context window next
    to its gauge (`ctx ▰▰▰▱▱▱▱▱▱▱ 31% 63k/200k`), rounded down. Output tokens
    are not counted, like in the percentage.
  - Add the `dotfiles_codex` tag: when `codex` is installed it sets
    `status_line` in the `[tui]` table of `~/.codex/config.toml` (model,
    directory, branch, context used, tokens, 5-hour and weekly limits) and
    leaves the rest of the file alone. A file Codex could not load stops the
    play unchanged; a layout the edit cannot handle is restored.
  - Install `claude-code`, `claude-desktop` (AUR) and `openai-codex` with the
    `10_sre_devops` group on Arch.

### Changed

- **Dotfiles**:
  - Copy `~/.vim` and the Zsh tree (`~/.local/share/dotfiles/zsh`) instead
    of linking them into the target's clone, and copy the Hyprlock background
    as well. Once deployed, the home
    directory no longer uses `~/.dotfiles`, which can be deleted. Only the
    files Git tracks are copied. A deployment replaces an old link into
    `~/.dotfiles` with a copy and brings over what programs had added there
    (Vim backups, swap files). Check mode lists those files and stops before
    the replacement.
  - Drop Vundle and tpm. The Vim plugins are cloned on the target at the
    commits pinned in `dotfiles_vim_pack_plugins`, into the Vim package
    `~/.vim/pack/dotfiles/start/`, which Vim loads at startup. Deployment
    never ran `:PluginInstall`, so most declared plugins were missing; they
    are all there now. vim-instant-markdown is actually loaded for the first
    time since 2021, when it moved out of the `after/` directory that Vundle
    was told to load. Its preview no longer starts on its own
    (`:InstantMarkdownPreview`), because it reports an error on every
    Markdown buffer without the `instant-markdown-d` server. The settings
    `.tmux.conf` took from tmux-sensible, which tpm never installed, are
    written in the file.
  - Remove what Vundle and tpm left in the home: `~/.vim/bundle/`,
    `~/.tmux/plugins/`, and `~/.tmux` once it is empty (a `~/.tmux` link
    into `~/.dotfiles` loses only the link). A Git repository there with
    uncommitted changes, a stash, or commits that no remote branch holds
    stops the deployment before anything changes. Check mode lists what
    would be removed. What they wrote into the clone through a link stays
    there.
  - Install `instant-markdown-d`, the server behind
    `:InstantMarkdownPreview`, on Arch with the AUR package
    `nodejs-instant-markdown-d` in `01_base`. The deployment now stops when
    the package for the host's OS family (`dotfiles_vim_preview_packages`,
    read through `package_facts`) is missing; check mode only warns. Debian
    and Fedora package no such server, so nothing is installed or checked
    there and the preview stays unavailable.
  - `vim.tar.gz` ships the pinned plugins, without their Git metadata, so
    `scripts/vim.sh` no longer needs Git: it only downloads and extracts the
    archive. The package jobs read the plugin list from the role defaults
    with `scripts/ci/fetch_vim_plugins.py`.
  - Replace the Zsh plugin submodules with clones on the target, pinned in
    `dotfiles_zsh_plugins`. The repository has no submodules left. To update
    a plugin, change its commit there; the next deployment moves the clone
    and removes the files dropped upstream.
  - Record the files copied into each directory in
    `~/.local/state/dotfiles/manifests/`. The next deployment deletes those
    the repository no longer ships, such as `_fwupdmgr`, unless they were
    changed on the target; files added by hand stay.
  - `dotfiles_trees` replaces `dotfiles_links`, `dotfiles_zsh_dest` replaces
    `dotfiles_zsh_link_dest`, and `dotfiles_repository` is gone. The
    `dotfiles_submodules` tag and the `dotfiles_submodule_update` module are
    removed. `dotfiles_vim_pack_plugins` replaces `dotfiles_vim_plugins`;
    `dotfiles_update_vim_plugins`, the `dotfiles_runtime` and `vim` tags and
    `dotfiles_plugin_managers` are removed, as is `copy: false` in
    `dotfiles_trees`. `dotfiles_retired_plugin_paths` and
    `dotfiles_retired_plugin_parents` list what the deployment removes.
  - Drop `make` from the Zsh plugin list: no such plugin was ever shipped,
    so Zsh skipped it.
- **Makefile**:
  - `make deploy` runs a playbook on `HOST`, and `make check` previews the same
    run in check mode. `PLAYBOOK` (`site` or `obs`), `TAGS`, `SKIP_TAGS` and
    `BECOME_PASS=1` replace the `--tags`, `--check` and `--ask-become-pass`
    options written in `ANSIBLE_ARGS`, which still passes any other option.
  - Add `make plan` (package plan only), `make tags` and `make tasks` (what a
    `TAGS` selection runs) and `make verify` (lint, then tests). `make help`
    also lists the variables. `make tags` and `make tasks` ignore
    `BECOME_PASS`, as listing needs no sudo password. `make plan` refuses
    `TAGS` and `SKIP_TAGS`: the plan stops at a task of the `packages` role,
    and a selection that skips it would let the `dotfiles` role deploy.
  - `make galaxy` installs the collections pinned in `ansible/requirements.yml`
    that are missing or at another version, into `.ansible/collections`.
    `make galaxy-force` reinstalls them with `--force`.
  - `make install` and `make install-obs` remain as aliases, and
    `make install install-obs` runs both playbooks. A `PLAYBOOK` that is not
    exactly one of `site` and `obs` stops with the list of valid ones (a `%`
    in it is not a wildcard), and the
    backup targets now also use the repository `ansible.cfg` explicitly.
- **CI**:
  - The unit test and Ansible lint jobs install their collections with
    `make galaxy`, so both use `.ansible/collections` and the Makefile command.
- **Ansible roles**:
  - Split the `system` role into one role per function: `lact`, `gaming`,
    `package_services`, `docker`, `hardening`, `dns`, `vpn`, `gpu` and
    `cpu_power`. The `system` tag still runs all of them, and every former
    task tag still works.
  - Move the pacman and makepkg settings into the new `package_manager` role,
    which runs before the packages are installed.
  - Move the Claude Code and Codex status line settings out of `dotfiles` into
    the new `agent_cli` role.
  - The playbooks select the package groups first under the `always` tag, so
    the `packages` role no longer lists the tags of the roles that read the
    selection. The `packages_select` tag is gone.
  - With `packages_action=plan`, every role that changes the host is now
    skipped, including makepkg, hardening, GPU and AMD CPU settings when they
    are run by tag.
  - Rename the role variables after their new role, for example
    `system_dns_manage` to `dns_manage`, `system_ipv6_enabled` to
    `hardening_ipv6_enabled`, `system_power_manager_conflict_action` to
    `gaming_power_manager_conflict_action` and `dotfiles_claude_statusline` to
    `agent_cli_claude_statusline`. A host override or `-e` option that uses an
    old name is ignored.

- **Ansible hosts**:
  - The playbooks reach the workstations over SSH. `ansible/inventory.yml`
    lists PadsTower and PadsP5560, and each machine's settings are in
    `ansible/host_vars/<hostname>.yml`. The shared groups are listed once in
    `packages_workstation_groups` (`group_vars/all/packages.yml`).
  - `make install` and `make install-obs` target `HOST`, which defaults to
    the short hostname (`uname -n` up to the first dot): `make install HOST=PadsP5560` configures the laptop from
    another machine. The backup targets still read the local home.
  - The facts are gathered as the SSH user (`tasks/target.yml`), and a play
    stops when the machine reports another hostname than its inventory name.
  - The roles read the home, user, `PATH`, `XDG_STATE_HOME`, PCI devices and
    OBS helper scripts on the target instead of the controller.
  - The Vim, tmux and Zsh links point into the target's clone,
    `dotfiles_repository` (default `~/.dotfiles`), and deployment stops when
    it is missing.
  - Upgrade: a target needs an SSH server that accepts the user's key, and
    this repository cloned in `~/.dotfiles`. A new machine must be added to
    the inventory.
  - Upgrade: `ansible/host_vars/localhost.yml` is gone, and so are the maps
    keyed by hostname. `packages_host_groups` is now a list, and
    `system_ipv6_enabled_by_hostname` and
    `dotfiles_hypridle_enabled_by_hostname` become the booleans
    `system_ipv6_enabled` and `dotfiles_hypridle_enabled`. The packages role
    fails with a clear message when `packages_host_groups` is still a map.
- **DNS**:
  - Link `/etc/resolv.conf` to the resolved stub. A regular file that another
    program owns, such as a connected VPN client, is reported and kept.
  - Remove the NetworkManager `dns.conf` and the `rc-manager.conf` of the
    former install guide when they set nothing but the DNS mode.
  - On hosts with the former dnsmasq relay, stop `dnsmasq.service`, remove the
    relay files, and move automatic profiles that used it back to DHCP DNS.
    Removed files are backed up under `/var/lib/dotfiles/dns-backup`.
  - With Docker, pin `docker0` to `10.184.1.1/28` (Docker's default is
    `172.17.0.1/16`) and use resolved as the containers' DNS server, VPN split
    DNS included. Containers on the default bridge change address, that bridge
    holds at most 13 of them, and `docker.service` needs a restart.
- **Ansible dotfiles**:
  - The icon theme is set once with `dotfiles_icon_theme` (default
    `Papirus-Dark`) and rendered into `.gtkrc-2.0`, GTK 3 `settings.ini`,
    `hyprtoolkit.conf` and the Mako `icon-path`. Mako also searches
    `dotfiles_icon_theme_parent`, which by default drops a `-Dark` suffix.
  - nwg-look no longer exports `.gtkrc-2.0` or GTK 3 `settings.ini`, which
    Ansible now renders.
  - A changed Mako config reloads Mako, and a changed `hyprtoolkit.conf`
    restarts Hyprlauncher. Other rendered files no longer trigger these
    handlers.
  - Render the host-dependent files from variables instead of shipping a copy
    per hostname: the Waybar `config` and `conf/temperature.json`,
    `hypridle.conf` and the Hyprland `hosts/settings.lua`. The templates hold
    no host logic. PadsTower and PadsP5560 set their values in
    `host_vars/<hostname>.yml`; the monitors and workspaces they share
    are in the new `group_vars/all/main.yml`.
  - A machine is portable when the `form_factor` fact says so, or when
    `dotfiles_is_portable` is set. Waybar then shows the backlight and
    battery, and Hyprland turns off blur and shadows.
  - Hyprland no longer loads `hosts/<hostname>.lua`: `include/host.lua`
    applies `hosts/settings.lua`, and a change to that file reloads Hyprland.
    `hosts/common.lua` and `is-host.sh` are removed.
  - The PadsTower suspend after one hour is now
    `dotfiles_hypridle_suspend_timeout: 3600`. Other hosts default to 0, which
    never suspends.
  - The role validates its settings before changing anything and has a
    `meta/main.yml`. Rendered files get an explicit owner, group and mode
    (`dotfiles_template_mode`, default `0644`).
  - Upgrade: monitors are described by relations instead of `hl.monitor()`
    tables (see the Hyprland entry under Fixed), and
    `vault_dotfiles_monitor_outputs` and `vault.yml-example` are gone. The
    `~/.config/waybar/config` link to
    `config.<hostname>` is replaced by a rendered file, and
    `dotfiles_waybar_host_config` is gone.
  - `hypr-screenshot.sh` renders a generic Waybar config and empty Hyprland
    host settings for its demo home. Its `WAYBAR_CONFIG` variable is gone.
- **CI**:
  - `scripts/ci/run_unit_tests.py` replaces `run_unit_tests.sh` for GitLab CI,
    `make test-python` and `make coverage`. It runs each slow test in its own
    process and packs the fast tests of a module into one, then starts the
    longest first. Durations come from the previous run
    (`.cache/unit-tests/durations.json`, kept in the GitLab cache); tests
    without one run one process per class. The run fails if fewer tests ran
    than were discovered.
  - `JOBS` defaults to the usable CPUs, capped by the container CPU quota and
    by its memory limit (300 MiB per worker).
  - The `unit_tests` job caches pip downloads and the Ansible collections.
  - The template test of `test_dotfiles_deploy.py` skips the `systemd` tag:
    user units have their own regression test, and deploying every shipped
    unit made each run three times longer.
- **Documentation**:
  - The Arch install guide installs `systemd-resolvconf` instead of
    `openresolv` and links `/etc/resolv.conf` to the resolved stub.
  - The README opens with the animated demo.
- **Scripts**:
  - `hypr-screenshot.sh` also records an animated WebP demo
    (`dist/hyprland-demo.webp`): a Hyprlauncher search, a Mako notification,
    then Hyprlock.
  - Captures run as `demo@dotfiles` in namespaces, with an empty environment
    and a home built from the repository: no real user, host or session
    detail shows up. `EDITOR_FILE` is now relative to the repository.
  - Frames are reproducible: fixed resolution, no animations, hidden pointer,
    pinned wallpaper. Images are written atomically.

### Fixed

- **tmux**: true color works again. The `terminal-overrides` line for mouse
  scrolling replaced the list instead of appending to it, which dropped the
  `RGB` override set at the top of `.tmux.conf`.
- **Hyprland**:
  - The cursor can move between every monitor again on PadsP5560. The laptop
    panel was fixed at `0x1440`. The Dell and ASUS rules were dropped without
    `vault_dotfiles_monitor_outputs`, so Hyprland placed those monitors to the
    right of the panel, and the panel touched the Dell only at a corner.
    `include/layout.lua` now computes the positions from relations
    (`right_of`, `left_of`, `above`, `below`) and from the size each connected
    monitor reports, and computes them again on hotplug and once Hyprland
    has applied the mode and scale. A monitor that is
    not described, or whose neighbour is missing, joins the right edge of the
    layout, so every monitor stays reachable. `dotfiles_hypr_monitors` gives
    each monitor a unique name and finds it by the start of its EDID
    description (`match`) or as the built-in panel (`internal: true`).
    Identical models pair in connector order unless `match` includes the
    serial number, and their rules follow their connector. Mode
    and scale are no longer written anywhere: `dotfiles_hypr_monitor_mode`
    chooses `preferred` (the default), `highrr` (PadsTower) or `highres`, and
    the scale is `auto`, as in the generic rule of `conf/monitors.lua`.
    `dotfiles_hypr_touch_output` becomes `dotfiles_hypr_touch_monitor`, a
    monitor name.
- **Zsh**:
  - Append the plugin directories and the `zsh-completions` sources to
    `fpath` before `compinit`. They were added after it, so the plugin
    completions (`httpie`, `docker-compose`, `hub`) and every
    `zsh-completions` function were never registered. They go last, so the
    completions shipped by zsh and the packages (`docker`, `age`) win.
  - Drop the bundled completions that hid the ones from zsh or the packages.
    `_ansible` only knew `ansible` 2.0 and hid zsh's, which covers every
    Ansible CLI (`ansible-playbook`, `ansible-galaxy`, ...). `_hugo` held a
    bare `$(...)` line, so `hugo` had no completion. `_yay`, `_gsettings`,
    `_logger` and `_shutdown` were older or identical copies. `_fwupdmgr`
    lacked twenty commands of the `zsh-completions` one (`security`,
    `sync`, `inhibit`, `get-bios-settings`, ...).
  - Rewrite the host name completion as `_dotfiles_hosts`, used by ssh, scp,
    rsync, ping and the other commands that complete hosts. It now follows
    every `Include` of `~/.ssh/config` (it only read `config.d/*`), reads
    `Host` lines in any case or with `=`, and `Match host` lines. It reads
    `/etc/ssh/ssh_known_hosts` (the path was wrong), still reads the
    `known_hosts2` files and skips `@revoked`
    entries. Without `~/.ssh/config.d`, each TAB printed `no matches found`.
  - Rebuild the completion dump once a day as intended. The `(#q)` glob
    qualifier needs `extended_glob`, which is off there, so every shell ran a
    full `compinit` scan.
- **Docs**:
  - List every Hyprland shortcut in the README. The table claimed Vim keys
    that are not bound and left out window closing, `ALT + Tab`, the password
    manager, `[` / `]` focus, mouse move and resize, sending a window to a
    workspace without following it, relative workspaces, the wallpaper key and
    zoom.
- **Packages**: send missing packages from the official repositories to pacman
  again. The repository listing regex had doubled backslashes, matched nothing
  on current ansible-core, and handed every missing package to yay, which
  cannot use sudo without the become password.
- **Ansible**:
  - The `docker_daemon_dns` and `lact_config` filters no longer deep-copy
    Ansible's lazy containers. The copy also copied the templar, and rebuilding
    its plugin loaders printed `PluginLoader with aliases` deprecation warnings
    (seen with ansible-core 2.22).
  - Run sudo with `TERM=dumb` (`ansible.cfg`, `[sudo_become_plugin]`). Since
    systemd 258, pam_systemd writes an OSC 3008 escape sequence to the
    terminal when the sudo session closes. Ansible runs become tasks over
    `ssh -tt`, so that sequence followed the module JSON and every become
    task printed an empty `Module invocation had junk after the JSON data`
    warning.
  - Stop shipping the `gnome-session.target.wants/tracker-miner-fs-3.service`
    and `tracker-miner-rss-3.service` links. Tracker 3 is now `localsearch`,
    whose units are static and started over D-Bus, so both links were broken
    in `~/.config/systemd/user`. Deployment removes them from existing homes
    (`dotfiles_obsolete_user_unit_links`) when they are still symlinks, and
    the `check-symlinks` pre-commit hook no longer excludes them.
  - `package_services` enables `bluetooth.service` only when the kernel lists
    a Bluetooth controller (`/sys/class/bluetooth/hci*`). Hosts without one
    got a unit that could not start; the skipped unit is now reported, and
    other units can declare a device the same way
    (`package_services_device_requirements`).
- **DNS**:
  - Stop the relay `dnsmasq.service` before removing the relay files. Those
    files are how the role recognises the relay, so a run interrupted between
    the two steps left dnsmasq running for good.
  - The port 53 check ignores the relay dnsmasq by its main pid instead of by
    name, so another dnsmasq on all addresses now stops the play.
  - With Docker, check that resolved listens on the bridge address over UDP
    and TCP before writing `daemon.json`. resolved only logs a stub listener
    it cannot bind, so containers could be left without DNS.
- **Pages**:
  - The documentation site publishes every Markdown file of the repository,
    not just five of them, and the Pages jobs run when any `.md` file changes.
    Links to `ansible/README.md`, `dist/arch/dns-migration.md` and other
    unpublished pages returned 404.
  - Relative links are rewritten for the site: Markdown links go to their page,
    images are copied, and links to other repository files go to the forge's
    file browser at the built commit. The README link to the CI workflows page
    pointed to `.github/`, which GitHub Pages does not deploy.
  - A link to a missing file now fails the Pages build, and the
    `test-gen-pages` pre-commit hook checks the site on every Markdown change.
  - The Pages jobs also run when only an image changes.
- **Scripts**:
  - `hypr-screenshot.sh` no longer runs the Hyprland autostart (gsettings,
    polkit, cliphist) in the live session.
  - The showcase terminal shows fastfetch again.
- **Tests**:
  - `make` no longer passes Git's repository variables (`GIT_DIR`,
    `GIT_INDEX_FILE`, and the rest of `git rev-parse --local-env-vars`) to its
    commands. A commit from a linked worktree runs the `test` hook with
    `GIT_DIR` set, and the tests that create their own repositories then
    reinitialised this one: `core.bare=true`, plus their `user.name`,
    `user.email` and `commit.gpgsign=false` in `.git/config`.

## [v6.2.0](https://gitlab.com/pad92/dotfiles/-/releases/v6.2.0)

### Added

- **CI**:
  - Add GitLab IaC scanning for Ansible configuration.
- **Claude Code**:
  - Add a one-line status line (`~/.bin/claude-statusline`) matching the Zsh
    theme: model, effort, directory, Git state, merge request, context gauge,
    subscription limits with the time left before each reset, and changed
    lines.
  - Merge its `statusLine` entry into `~/.claude/settings.json` with the
    `dotfiles_claude` tag, only when the `claude` binary is installed.
- **Graphics**:
  - Detect hybrid graphics at deployment and session startup, and enable NVIDIA
    runtime power management on supported battery-powered laptops.
- **SSH**:
  - Keep the Proton Pass SSH agent running as a user service and select its
    D-Bus keyring in shells that use it.
- **Hyprland**:
  - Allow hypridle to be enabled or disabled per hostname. Disabled hosts stop
    the user service and prevent it from starting automatically.
  - Dismiss all notifications with `SUPER+N`; `SUPER+SHIFT+N` restores the
    last one.
- **Waybar**:
  - Add NVIDIA PowerMizer profiles while keeping the existing AMD profiles.
- **Ansible system**:
  - Ask whether to stop, disable, and uninstall a CPU power manager that
    conflicts with `power-profiles-daemon` instead of failing
    (`system_power_manager_conflict_action`: `ask`, `remove`, or `fail`).
  - Enable the services of selected package groups on Arch Linux (Bluetooth,
    CUPS, Docker, `fwupd-refresh` timer) and add the deploying user to the
    `docker` group.
  - Restart `ananicy-cpp` when the playbook installs or updates its rules
    package.
  - Persist the AMD EPP and X3D settings applied by Ansible in
    `/etc/tmpfiles.d/dotfiles-amd-cpu.conf` so they survive reboots.
- **Tests**:
  - Add `make coverage` with a pinned coverage.py, a 98% floor in `.coveragerc`,
    and a Cobertura report in GitLab CI.

### Changed

- **CI**:
  - Run the Python unit tests in parallel, one process per test file, in
    GitLab CI, `make test-python` and `make coverage`
    (`scripts/ci/run_unit_tests.sh`, `JOBS=N`). Coverage data from each
    process is combined before the report.
  - Shorten the slowest deployment test by keeping only the Waybar files it
    checks in its temporary role copy.
  - Route all GitLab jobs, including included scanner jobs, to the `chataigne`
    runner and use the current built-in SAST and Secret Detection templates.
  - Package Vim configuration only on branch pushes and merge requests that
    change `.vim/` or `.vimrc`.
- **Hyprland**:
  - Use the detected boot GPU to order DRM devices, allowing application-level
    GPU offload to choose its own driver.
- **README**:
  - Reorganize the README around a quick start, a table of common commands,
    and collapsible details, with pipeline and release badges.
  - List the Ansible collections to install when only `ansible-core` is
    available, and document the `package_services` and `lact` tags.
- **Mako**:
  - Show at most five notifications instead of ten. Repeated notifications
    with the same application, summary, and urgency are merged into one.
  - Make the background translucent like Waybar's and blur it with a Hyprland
    layer rule.
  - Show the sending application above each summary. Low-urgency
    notifications get a grey border.
  - Match the corners, padding, and spacing to Hyprland's rounding and gaps.
    The progress bar uses Gruvbox blue.
- **Ansible**:
  - Remove the `./install` launcher. Run the playbook with `make install` and
    pass its options through `ANSIBLE_ARGS`.
  - Manage dotfile deployment, backups, Pacman operations, sysctl values, Vim
    checkouts, submodules, and sysfs controls through Ansible modules. The
    backup helper now only collects paths.
  - Report paths changed by package builds and Git submodules. Initramfs
    reporting covers the configured output directories.
- **Ansible packages**:
  - Remove `auto-cpufreq` from `01_base`; it conflicts with the
    power-profiles-daemon used for gaming.
  - Treat `packages_protected` as extra names on top of the built-in protected set.
- **Ansible system**:
  - Limit the Steam sysctl policy to `vm.max_map_count`; leave general VM,
    scheduler, network backlog, file-handle, and compatibility mmap settings at
    their kernel or distribution defaults.
  - Enable IPv4 forwarding only when a Docker or Podman group is selected.
- **Ansible dotfiles**:
  - Move conflicting symlinks to `.bak` instead of deleting them.
- **Vault**:
  - Make `.vault` optional: `make` exports it only when it exists, and
    `ansible.cfg` no longer requires it.
- **Waybar**:
  - Name LACT profiles after their PowerMizer modes and use the existing chip
    icon.

### Fixed

- **Arch Linux**:
  - Stop `clean_arch` from reporting a failed yay cache cleanup at random
    under `pipefail`: the `y` answer is now passed as a here-string, because
    a piped `echo` could die of SIGPIPE when yay exited without reading it.
- **CI**:
  - Build the Vim archive on every push to `main`, so its public download
    link keeps working. The job only ran when the Vim configuration changed,
    and no archive was left to download.
  - Install the pinned Ansible collections in the unit test job. The gaming
    tests failed because `community.general.pacman` could not be resolved, and
    four collection-dependent tests were skipped.
  - Install `make` in the CI test image and install the pinned Ansible
    collections. Install Git and configure Ansible's module paths and temporary
    configuration for world-writable checkouts.
- **Mako**:
  - Show critical notifications in do-not-disturb mode, which `steam-optimize`
    enables during games. They get a red border and stay until dismissed,
    even when the sender requests a timeout.
  - Draw notifications above fullscreen windows. They used Hyprland's top
    layer, which fullscreen windows cover.
  - Show icons from the Papirus-Dark GTK theme. Mako only searched `hicolor`
    and `pixmaps`, so names such as `dialog-warning` had no icon.
  - Install `mako` and `ttf-dejavu` with the default Arch Hyprland group. The
    role enabled `mako.service` without installing Mako.
- **SSH**:
  - Set Proton Pass's D-Bus keyring for local Zsh sessions.
- **Hyprland**:
  - Correct touch-device output and directional bindings, and use the numeric
    `drag_lock` value expected by Hyprland.
- **yay**:
  - Detect `curl` and `wget` commands piped to `sh` or `bash` in the PKGBUILD
    scan hook.
- **Ansible**:
  - Fix submodule path reporting, first Vim clones, backup and sysctl check
    mode, and initramfs change notifications. Avoid refreshing Arch package
    databases when a system upgrade is disabled.
- **Ansible packages**:
  - Continue with the system and dotfiles roles in check mode instead of ending
    the play after the package plan; keep the plan action read-only, including
    the Pacman repository configuration.
  - Pass `packages_protected` to reconcile removals on Debian and Fedora.
  - Count packages satisfied through `provides` as installed on Arch Linux.
  - Accept an empty package group selection.
  - Give `yay`/`paru` the Ansible become password through a temporary
    `SUDO_ASKPASS` program, so AUR packages install without a terminal.
- **Ansible system**:
  - Reload udev and replay the NVIDIA bind event when the runtime PM rule
    changes; report when a removed rule or legacy sysctl drop-in stays active
    until reboot.
  - Load the package group selection with the `system` and `kernel_hardening`
    tags, and warn when it is unavailable.
  - Read the current sysctl values in check mode so the preview keeps
    `vm.mmap_rnd_bits`.
  - Report missing gaming packages in check mode instead of failing.
- **Ansible dotfiles**:
  - Restart hypridle when `hypridle.conf` changes and the XDG desktop portal when
    its configuration changes; remind to log in again after UWSM environment
    changes.
  - Preserve conflict backups atomically and deploy hidden files, empty
    directories, and source links without following cycles indefinitely.

## [v6.1.0](https://gitlab.com/pad92/dotfiles/-/releases/v6.1.0)

### Added

- Show the power-profiles-daemon profile and ananicy-cpp service state in the
  Waybar LACT tooltip, including missing services and read errors.

- AMD P-State EPP configuration based on CPU facts and available kernel controls,
  with rollback on failure. Skip EPP changes when a known power manager is active
  or enabled; make X3D CCD mode opt-in. Settings apply until reboot.

### Changed

- Speed up repeated local `dotfiles_deploy` runs with one checksum comparison
  before copying static directories. Skip unchanged directories while keeping
  Ansible backups, targeted reloads and the regular copy path as a fallback.
- Keep successful user-unit symlink checks concise instead of printing nested
  file metadata for every item.

- Simplify user service handlers with systemd `try-restart` and
  `try-reload-or-restart`. Queue service jobs without blocking Ansible and
  relaunch Hyprlauncher as a UWSM service instead of waiting for its process.

- Load Ansible package variables by OS family, distribution, and version.
  Split system tasks by function and user systemd deployment into its own file.
- Replace GameMode in `21_steam` with `ananicy-cpp` and `power-profiles-daemon`;
  manage their services with Ansible. Select CachyOS rules, Proton, and
  `cachyos-settings` only on CachyOS, using its configured repositories.
- Let `steam-optimize` launch without `game-performance`. Set a 12 GB default
  shader cache for AMD and NVIDIA, with per-game overrides.
- Reload active audio services after configuration changes, or restart when
  reload is unavailable. Restart only active user units whose definitions or
  drop-ins changed; preserve masks, aliases, and activation links.
- Restart Hyprlauncher after deploying its configuration. Open the desktop
  finder with `SUPER+D`, with frequently used apps ranked first.
- Point the `mediasync` shell alias to `~/.local/bin/mediasync`.

### Fixed

- Load LACT test filters explicitly with an isolated Ansible configuration.
  This fixes GitLab CI failures when Ansible ignores `ansible.cfg` in a
  world-writable checkout.
- Normalize directory paths before the local deployment comparison so `./`
  prefixes and trailing slashes cannot cause files to be skipped.
- Refuse to replace a symlink used for LACT configuration. Accept custom or
  empty default profile sets on a first installation.

- Discover LACT GPU identifiers from the daemon and repair mismatched casing
  while preserving existing profiles. Manage the system configuration with
  backups under the `lact` tag instead of deploying a hardware-specific home
  configuration. Include cpupower and system76-power in CPU power-manager
  conflict checks.
- Discover optional AMD X3D controls instead of assuming a fixed ACPI device
  instance.

- Enable and start `hypridle.service` when deploying user systemd units.
- Unmask `power-profiles-daemon.service` before enabling it for `21_steam`,
  after checking for competing CPU power managers.
- Fix a `steam-optimize` crash when only one local Steam account configuration
  exists and the most recently used account cannot be identified.
- Remove the Hyprland music shortcut left behind after Spotify was removed;
  its missing command caused a configuration error at startup.
- Use relative links for the local wallpaper and Proton Pass user units.
  Preserve existing files that conflict with managed unit symlinks.
- Remove the GTK 2 include for the absent `~/.gtkrc-2.0.mine` file.

## [v6.0.1](https://gitlab.com/pad92/dotfiles/-/releases/v6.0.1)

### Fixed

- **GitLab Pages**: Deploy the documentation site from release tags and skip
  the review build in tag pipelines.

## [v6.0.0](https://gitlab.com/pad92/dotfiles/-/releases/v6.0.0)

### Added

- **CI**: Build downloadable Neovim configuration archives with GitHub Actions
  and GitLab CI.
- **Ansible**: Add configurable NVIDIA kernel options, capability-gated i915
  GuC settings, and automatic initramfs regeneration when those settings change.
- **Ansible**: Add `make ansible-backup-ls` to list Ansible-managed dotfile
  backups and `make ansible-backup-rm` to remove them after confirmation.

### Changed

- **Breaking — installation**: Replace the Dotbot installer with Ansible for
  package selection, system setup, and dotfile deployment. Support Arch
  Linux/CachyOS, Debian/Ubuntu, and Fedora.
- **Dotfiles**: Move static home configuration into the dotfiles role, render
  host-aware files from templates, and link the Vim, tmux, and Zsh source trees.
  Back up conflicting regular files and directories before deployment, and stop
  when a required backup already exists. Reload Mako, Waybar, and the user
  systemd manager only after related files change. Skip Vim checks and plugin
  updates unless explicitly enabled, and remove the `font_cache` tag.
- **CI and scripts**: Move shared CI helpers to `scripts/ci/` and the Vim setup
  script to `scripts/vim.sh`; update workflow and documentation references.
- **Packages**: Select GPU profiles from detected hardware and support explicit
  package reconciliation. Configure pacman progress options (`ILoveCandy` on
  Arch Linux, `PrettyProgressBar` on CachyOS), enable `multilib` when needed,
  and build `yay` from the AUR to install selected packages.
- **Arch builds**: Use native CPU flags for makepkg and disable debug packages.
- **Ansible**: Add focused tags for pacman, AUR, makepkg, and dotfiles tasks.

## [v5.6.0](https://gitlab.com/pad92/dotfiles/-/releases/v5.6.0)

### Added

- **Installation**: Automatically preselect AMD, Intel, NVIDIA, and hybrid
  Intel/NVIDIA graphics-driver groups from detected PCI hardware, and safely
  remove installed driver packages that belong only to unselected GPU profiles.
  Preselect the base, GTK, and Hyprland package groups as standard defaults.
- **Installation**: Add selectable SRE/DevOps, container-runtime, IaC, GPU-driver,
  and vendor-specific printer package groups.
- **AWWW**: Add configurable local and mounted NFS/CIFS sources, including
  multiple directories and automatic local fallback. Preserve image ratios with
  blurred backgrounds and optional date/city metadata.
- **Hyprlock**: Add an AWWW-backed lock screen to Wlogout. The background
  advances to another photo every minute; blur and metadata follow the AWWW
  settings, and the clock uses its configured metadata font.

### Changed

- **Docs**: Document AWWW source, rendering, and troubleshooting options.
- **Zsh**:
  - Centralize and deduplicate `PATH` setup in `.zshenv`, with user binaries
    taking precedence consistently in login, interactive, and nested shells.
  - Move UWSM startup to `.zprofile`, restrict Fastfetch to top-level terminals,
    and cap saved command history at 100,000 entries.
- **Hyprlock**:
  - Update the animation, DPMS, and sleep-lock settings for Hyprlock 0.9.6 and
    Hypridle 0.1.8.
  - Show the website behind browser media, including service-specific names and
    icons for Deezer, YouTube, and other common streaming sites.
  - Escape player metadata and limit artwork downloads, conversions, cache size,
    and retry frequency.
  - Keep a cached cover when the same URL fails to refresh or Firefox removes
    its temporary MPRIS image. Artwork refreshes every 3 seconds so the script
    can save that image before it disappears.
  - Detect USB, USB-C, USB-PD, and wireless chargers in the lock-screen power
    status.

### Fixed

- **Installation**: Keep LACT as an explicit import template. Preserve all saved
  GPU choices after partial detection and stop without rewriting package state
  when an inventory fails. Require managed ownership and explicit confirmation
  before removing an old GPU driver profile.
- **AWWW and Hyprlock**: Reject invalid configuration and unreadable images,
  including when effects are disabled. Bound carousel attempts and duration,
  with a local fallback in auto mode. Expire managed renders after 30 days and
  enforce a configurable 2 GiB quota while preserving current backgrounds.
- **CI**: Install ImageMagick, retain Python's executable path, and cover package
  inventory errors, partial GPU detection, carousel timeouts, and cache eviction.
- **Zsh**: Treat an empty orphan list as a successful cleanup and keep recursive
  Git pulls on the current branch when a fast-forward is not possible.
- **Arch packages**: Restore alphabetical order in the AMD and SRE/DevOps lists.
- **Installation**: Replace removed Arch package names, remove conflicting power
  managers and redundant transitive dependencies, and count packages only once
  when multiple selected groups overlap. Track packages installed by the
  dotfiles installer and provide read-only planning plus opt-in, confirmed
  reconciliation of packages that are no longer selected. Stop the backup job
  from automatically removing every orphan package outside that managed state.
- **AWWW**: Render wallpapers at each monitor's scaled pixel dimensions so they
  fill mixed-DPI and HiDPI displays instead of appearing small and centered.
- **Steam Optimize**: Select the active Steam account correctly, avoid mixed AMD
  and NVIDIA driver overrides on hybrid systems, preserve the inherited
  Hyprland session, and restore mouse DPI only from valid command output.
- **Zsh**: Stop reloading `/etc/profile.d` in every interactive shell and remove
  redundant completion, color, path, and editor initialization.

## [v5.5.3](https://gitlab.com/pad92/dotfiles/-/releases/v5.5.3)

### Fixed

- **AWWW**: Start the wallpaper timer after UWSM has imported the Hyprland
  session environment, so the initial wallpaper is applied at login.
- **CI / Pages**: Preserve two-space nested lists when generating HTML instead
  of flattening child items into the parent list.

## [v5.5.2](https://gitlab.com/pad92/dotfiles/-/releases/v5.5.2)

### Added

- **Zsh**: Add `mtail` to follow multiple files or quoted glob patterns with
  filename prefixes. It scans for new matches every second and uses `tail -F`
  to handle rotation and recreation. `Ctrl+C` cleans up its followers and
  temporary files without closing the calling shell.

### Changed

- **Desktop session**:
  - Move host-specific GPU settings from the common UWSM environment to
    `env-hyprland`. UWSM now sets the session's `XDG_*` variables.
  - Restrict AWWW, Hypridle, Mako, and Waybar user units to Hyprland sessions,
    and start `nm-applet` through XDG autostart outside KDE and GNOME.
  - Cycle through every available audio sink from Waybar, wrapping back to the
    first sink, and open `pavucontrol` with a right click.
- **Installation**:
  - Separate official repository packages from AUR candidates and remove
    duplicates from the selection. Report a missing `multilib` repository and
    each AUR package that fails to install.
  - Reuse an installed `paru` or `yay`, or offer to build `yay-bin` as a regular
    user after installing its official build dependencies.
  - Refresh the Arch package lists and installation guide for current package
    names, required desktop components, `sudo`, and `multilib` setup.
  - Update the Dotbot submodule.
- **Docs**: Rewrite and shorten the README. Setup instructions are now separate
  from the shell, desktop, script, and release documentation.

### Fixed

- **Hyprlock**:
  - Centralize the lock-screen palette variables.
  - Refresh player labels every second, battery status every 10 seconds, and
    artwork every 5 seconds instead of leaving the display unchanged.
  - Replace obsolete general options with the `fadeIn` animation setting for
    Hyprlock 0.9.6.
  - Identify media sources by `playerName` and use the Nerd Font Firefox glyph.
  - Use a transparent image when artwork is missing or cannot be processed.
    Cache covers by URL and publish converted PNGs with an atomic rename.
  - Keep the battery display independent of device order, show a percentage
    for each system battery, and exclude peripheral batteries.
- **Installation**:
  - Resolve the Dotbot configuration from the repository path, so `install`
    works when invoked outside the dotfiles directory.
  - Read menu input directly from the terminal and check `pacman`, `sudo`, and
    credentials before installing packages. If the user declines the AUR helper,
    skip AUR packages instead of sending their names to `pacman`.
- **Desktop**:
  - Override PipeWire's existing realtime module settings instead of loading a
    duplicate module.
  - Stop the logout menu from terminating the whole user session when both UWSM
    and Hyprland dispatch fail.
- **Yay**: Load hooks with yay's embedded Lua runtime. Invalid maintainer state
  now produces a warning instead of aborting the upgrade.
- **Portability**: stop tracking machine-generated systemd activation links and
  the package-provided `_yay` completion symlink; ignore them when generated
  locally.
- **Steam-Optimize**:
  - Detect failed helper commands instead of treating non-zero exits as
    successful.
  - Set and restore the mouse's detected DPI using the correct `razer-cli`
    option instead of silently treating the device-selection option as a DPI
    change.
  - Limit installer changes to Steam's most recently used account, validate all
    inputs before shutting Steam down, and report partial save failures.
  - Atomically replace `localconfig.vdf` after writing a durable temporary file,
    keeping a backup of the previous file and avoiding truncated Steam
    configuration files after an interrupted save.
  - Preserve the existing Mako notification modes when temporarily enabling
    do-not-disturb.

## [v5.5.1](https://gitlab.com/pad92/dotfiles/-/releases/v5.5.1)

### Changed

- **Hyprland**:
  - Factor the duplicated Dell monitor block and its workspace 2 rule, plus the shared ASUS monitor output/position/scale (only the refresh rate differs per host), out of `hosts/PadsTower.lua` and `hosts/PadsP5560.lua` into a new shared `hosts/common.lua`.
  - Factor the ad-hoc hostname check in the PadsTower suspend listener (`hypridle.conf`) into a shared `is-host.sh` helper, reusable by any future host-conditional listener.
  - Document the Gruvbox Dark palette duplicated across `hyprtoolkit.conf`, `hyprlock.conf`, `.config/mako/config`, `waybar/style.css` and `.tmux.conf` with cross-referencing comments, so future theme edits don't silently drift out of sync.
- **Zsh**:
  - Normalize inconsistent style: `if [ $(command -v x) ]` guards now use `command -v x &>/dev/null` throughout, and mixed `function foo {}` declarations now use `foo() {}` consistently across `zsh/functions/*.zsh`.
  - Collapse three redundant `rehash` calls in `.zshrc` into one, run once after all `PATH` mutations.
  - Document the security tradeoff of `gpg --trust-model always` in `crypt.zsh` (kept deliberately; skips the web-of-trust check).
- **Scripts**:
  - Add `set -uo pipefail` to `bin/diff-cmd` and `bin/vscodium_ext.sh`.
- **Steam-Optimize**:
  - Trim the Forza Horizon 5/6 profile down to its confirmed-working overrides: drop `single_queue` from `VKD3D_CONFIG` (a hang workaround for older vkd3d-proton releases that serializes GPU queues and costs performance), and remove the untested `SDL_VIDEODRIVER=x11` and `WINEDLLOVERRIDES` entries, which had no observed effect on the current Proton stack.
  - Factor the duplicated Grand Theft Auto V / Enhanced profile into a shared `_GTA_PROFILE`.
  - Centralize the `UserLocalConfigStore` → `apps` VDF path traversal (duplicated across `get_app_entry`, `get_app_entry_safe`, and the installer's launch-options reader) into a single `get_apps_dict()` helper.
  - Simplify `NotificationCollector`'s duplicated `__init__`/`start` reset logic into a shared `_reset()`.
  - Replace the magic `icon` parameter (`1`/`0`/`3`/`None`) on `log_msg` with an explicit `notify` boolean.
  - Compose the override notification label from a list of active fragments (wayland/battleye/dpi/env) instead of an `elif` chain that silently dropped fragments when several applied at once.
- **CI**:
  - Narrow the flake8/black `bin/` exclusion in `.pre-commit-config.yaml` to just `bin/steam-optimize` (pending a dedicated formatting pass); `bin/razer_dpi.py` is now PEP8/black-compliant and linted.
- **Docs**:
  - Document `bin/hypr-screenshot.sh`, `comcut`, `comskip.sh`, `diff-cmd` and `vscodium_ext.sh` in the README's Custom Scripts section, and mention `dist/*_excludes.txt` next to `backup.sh`.
  - Add the missing `v3.0` release notes to `CHANGELOG.md`, reconstructed from `git log v2.1..v3.0`, and correct/clarify which older entries are retrospective summaries.

### Fixed

- **Hyprland**:
  - Turn the screens back on when resuming from the 1h-inactivity suspend on PadsTower (`hypridle.conf`). The suspend listener had no `on-resume`, so the monitors stayed off after wake.
- **Zsh**:
  - Fix the `history` alias always falling back to the default format (`zsh/init/history.zsh`, `.zshrc`): `HIST_STAMPS` was exported in `.zshrc` _after_ `init.zsh` had already sourced `init/history.zsh` and built the alias from it, and the exported value (a `strftime` pattern) never matched the alias's keyword-based `case`. Export `HIST_STAMPS`/`HISTFILE`/`HISTSIZE`/`SAVEHIST` before sourcing `init.zsh`, and support arbitrary `strftime` patterns via `fc -t`, removing the now-redundant duplicate history block from `.zshrc`.
  - Merge `http_time` into `curl_time` (`zsh/functions/http_checks.zsh`, `curl.zsh`). The two were near-identical `CURL_FORMAT` timing helpers, and `http_time` mislabeled curl's `%{time_*}` values (always seconds) as milliseconds. `http_time` is now an alias to the corrected `curl_time`.
- **Scripts**:
  - Fix `make screenshot` writing a WebP file named `hyprland-showcase.png` at the repo root instead of `dist/hyprland.webp` (`Makefile`). The default `SCREENSHOT` path didn't match `hypr-screenshot.sh`'s own default output, which always encodes WebP regardless of the given extension.
  - Fix `bin/comcut`'s lockfile handling: the acquire loop was check-then-touch (racy under concurrent invocations) and never released the lock on error or signal, permanently deadlocking future runs after a crash. Acquire the lock atomically (`noclobber`) and release it via an `EXIT` trap.
  - Fix `bin/comcut` silently continuing after a failed `comskip`/`ffmpeg` invocation, which could produce a corrupted or partial output with no error reported. The relevant calls now abort the script on failure.
  - Fix `bin/comskip.sh` forwarding an unset argument to `comcut` instead of failing with a usage message.
  - Fix `bin/razer_dpi.py` always exiting `0`, even when no compatible mouse was found or every DPI write failed, hiding failures from callers (e.g. a systemd unit). It now exits `1` when nothing succeeded.
- **Steam-Optimize**:
  - Fix the `SIGTERM`/`SIGHUP` handler blocking indefinitely if the game process ignored `terminate()`; it now falls back to `kill()` after a 10s timeout.
  - Add `-a`/`--app-id` to force the AppID used for game-profile lookup and log tagging. Non-Steam game shortcuts report a generic `SteamAppId` (e.g. `480`/Spacewar) instead of the real store AppID, silently skipping the matching `GAME_PROFILES` entry. The override never touches the real `SteamAppId` env var inherited by the game process: forcing it to either the real store AppID or the shortcut's own internal AppID both crashed a Forza Horizon 6 non-Steam shortcut during CoreCLR startup. Any value other than Steam's own default breaks it, for a reason still unclear. This also means Steam Input can't find the shortcut's controller config, which keys off the same env var and is stuck on Spacewar's empty one; no fix found for that yet.
  - Add `-g`/`--no-gamescope` to skip the Gamescope wrapper entirely, for diagnosing whether a game's issue comes from Gamescope itself. Add a matching per-game `no_gamescope` profile flag.
  - Split Forza Horizon 6's profile out of the shared `_FORZA_PROFILE`. Its crash-on-launch and black-screen-with-audio symptoms had several independent causes, each requiring its own override: a forced `VKD3D_CONFIG` (FH5's `no_upload_hvv`, the community `enable_experimental_features,descriptor_heap` workaround, or `AMD_ENV_VARS`' global `dxr` default) crashes FH6 during CoreCLR startup on RADV on every Proton build tested except `proton-cachyos`; `COMMON_ENV_VARS`' `PROTON_ENABLE_WAYLAND` native-Wayland renderer and `AMD_ENV_VARS`' experimental `RADV_PERFTEST`/`ENABLE_LAYER_MESA_ANTI_LAG` each independently produce a black screen with audio still running; Gamescope itself produces the same black screen even with no forced resolution/output, and must be skipped entirely (known tradeoff: the game's own exclusive fullscreen then doesn't render under Hyprland either, so use windowed mode in-game instead); and `PROTON_FSR4_*_UPGRADE` injects an FSR4 upscaling shim that flickers green pixels on this title (a stale/corrupt `~/.cache/mesa_shader_cache` entry turned out to be the real cause of that last one, not the env var). FH6's profile now pops the driver overrides, skips Gamescope, keeps Steam Input on (its 8BitDo XInput translation is required, though it doesn't auto-activate for this shortcut and needs a manual overlay toggle on every launch, likely tied to the same `SteamAppId` issue), sets only `PROTON_SET_GAME_DRIVE=1`, and requires `proton-cachyos` as the compat tool.

### Removed

- **Zsh**:
  - Remove `zsh/functions/rambox.zsh`: hardcoded `dnf`/`rpm` for Fedora/CentOS, dead on this Arch-based setup.

## [v5.5.0](https://gitlab.com/pad92/dotfiles/-/releases/v5.5.0)

### Added

- **CI / Pages**:
  - Add a sticky navigation menu to every generated documentation page (`gen_pages.py`) linking Home / Changelog / Installation / CI Workflows / GitLab CI, with the current page highlighted and links resolved relatively so the site works under a subpath.
  - Render the documentation pages with their heading emoji/icons intact (`gen_pages.py`) and homogenize the icon style across all docs (README, changelog, install guide, and both CI READMEs).
  - Add `.github/workflows/README.md` documenting the workflows, the shared `.ci_bin/` scripts, and the multi-forge (GitHub/GitLab/Gitea) setup, and publish it to the docs site (mirroring its source path) via `build_pages.sh`.
  - Add `.gitlab/README.md` documenting the GitLab CI pipeline (stages, jobs, the `pages` build-vs-deploy rules, and the shared `.ci_bin/` scripts), and publish it to the docs site (mirroring its source path) via `build_pages.sh`. `build_pages.sh` also writes a `.nojekyll` marker so GitHub Pages serves the dot-directory pages verbatim.
  - Add a **Continuous Integration** section to the main `README.md` summarising the multi-forge (GitHub/GitLab/Gitea) setup and linking to both CI READMEs.
  - Document the variables/secrets in both CI READMEs: all tokens (`GITHUB_TOKEN`, OIDC, `CI_JOB_TOKEN`) are auto-provided, so no manual secrets are required; note the GitHub Pages / Gitea Actions one-time setup prerequisites.
- **Docs**:
  - Add a Hyprland desktop showcase screenshot (`dist/hyprland.webp`) as a hero illustration at the top of `README.md`, and refresh the Neovim feature list (treesitter `main`/Neovim 0.12, LSP `LspAttach` keymaps, gitsigns hunk/blame keymaps).
- **Hyprland**:
  - Suspend the machine after 1h of inactivity on PadsTower only (`hypridle.conf`). hypridle has no per-host mechanism, so the listener guards on the hostname; the laptop keeps its lock/DPMS-only behaviour.
  - Add screen zoom on `SUPER + PgUp`/`PgDn` (`Home` resets), driven via `hyprctl eval` + `hl.config` since the Lua parser disables `hyprctl keyword`, with an animated `zoomFactor`. Keyboard binds are used because Hyprland scroll binds leak the scroll event to the focused window ([#9319](https://github.com/hyprwm/Hyprland/issues/9319)).
- **Neovim**:
  - Add `neovim` and `tree-sitter-cli` to the Arch package list (`dist/arch/packages/20_apps.txt`). `neovim` was missing from the curated lists, and the nvim-treesitter `main` branch compiles parsers through the `tree-sitter` CLI (the `master` branch built them directly with `cc`).
  - Add LSP keymaps via an `LspAttach` autocmd (`lsp.lua`): `gd`/`gD`/`gi` (definition/declaration/implementation), `<leader>e` (diagnostic float) and `<leader>lf` (format), complementing Neovim 0.11's built-in `grn`/`gra`/`grr`/`K`. The LSP was previously configured but had no bindings.
  - Add gitsigns hunk keymaps via `on_attach` (`editor.lua`): `]c`/`[c` to navigate hunks, `<leader>gs`/`gr`/`gp`/`gd` to stage/reset/preview/diff, and `<leader>gb` to toggle inline blame.

### Changed

- **Tmux**:
  - Theme the status bar, panes, messages and copy mode with the Gruvbox Dark palette (`.tmux.conf`), aligned with waybar, gruvbox.nvim and hyprtoolkit, replacing the solarized plugin (`seebi/tmux-colors-solarized`) and a dead powerline include (hardcoded `python3.7` path, powerline not installed). Also enable true color (`tmux-256color` + `RGB` terminal override).
- **CI / Pages**:
  - Generate the Pages site in both `deploy-pages.yml` (GitHub) and the `pages` job (GitLab) by calling the reusable `.ci_bin/build_pages.sh` script instead of duplicating the `gen_pages.py` invocations, keeping the page list in a single source of truth. Made `build_pages.sh` POSIX `sh` and git-optional so it runs on minimal CI images (GitLab alpine).
  - Copy static assets referenced by the docs (the `dist/hyprland.webp` README showcase image) into `public/`, mirroring their source path, so relative `src` links resolve on both GitHub Pages and GitLab Pages (`build_pages.sh`).
  - Factor the CHANGELOG release-notes extraction shared by the GitHub and GitLab release jobs into a single POSIX `.ci_bin/extract_release_notes.sh` script, removing the duplicated `sed` logic.
  - Make `release.yml` forge-agnostic: create the release through the REST API (`POST /repos/{owner}/{repo}/releases` via `jq`/`curl`) instead of the `gh` CLI, so the same workflow runs on both GitHub and the Gitea runner (which also scans `.github/workflows`).
  - Guard the GitHub-Pages (`deploy-pages.yml`) and Vim-package (`package-vim.yml`) workflows with `if: github.server_url == 'https://github.com'` so they don't run on the Gitea runner.
  - Theme the documentation-site navbar with the Catppuccin palette (Mantle background, Mauve brand/active link) instead of Bootstrap's default `bg-dark`, and limit heading dividers to `h1`/`h2` to reduce visual clutter.
- **Hyprland**:
  - Output the isolated showcase capture (`bin/hypr-screenshot.sh`) as a web-optimised WebP (lossy, q80 via `WEBP_QUALITY`, max compression effort) instead of PNG. `grim` writes a temporary PNG that is re-encoded with the first available encoder (`cwebp`/`magick`/`convert`/`ffmpeg`).
  - Source the GTK theme name from `hyprtoolkit.conf` (`gtk_theme`) instead of hardcoding `Materia-dark-compact` in `config.lua`, keeping a single source of truth for theming.
  - Adopt physics spring animations for window open/move (`spring` curve `easy`) and align the full animation tree with Hyprland's upstream example, adding dedicated `layers`/`fadeLayers` animations for layer-shell surfaces (launcher, notifications, Waybar) and a `popin` effect on `windowsIn`.
  - Drop the 10-bit `bitdepth` override on the ASUS XG32WCS monitor (PadsTower), reverting to the default depth.
- **Neovim**:
  - Lazy-load Telescope (`cmd = "Telescope"`) and gitsigns (`event = "VeryLazy"`) instead of loading them at startup (`editor.lua`).
  - Move the Treesitter `foldmethod`/`foldexpr` out of the global `options.lua` into the per-filetype `FileType` autocmd in `treesitter.lua`, so folding is only set where a parser is actually started (alongside highlight/indent).
  - Point the Mason dependencies at `mason-org/mason.nvim` and `mason-org/mason-lspconfig.nvim` (the repos moved org), and drop the redundant manual `vim.lsp.enable("lua_ls")` now that mason-lspconfig's `automatic_enable` handles it (`lsp.lua`).
  - Default gitsigns `current_line_blame` to off (toggle via `<leader>gb`) instead of always-on inline blame (`editor.lua`).
  - Translate all configuration comments to English across the `nvim` config.

### Fixed

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
  - Fix fenced code blocks nested inside list items rendering as a plain paragraph (e.g. the `git clone … ./install` install snippet leaking `:::sh`). `gen_pages.py` now extracts every fenced block, dedents it, and renders it with Pygments before Markdown conversion, so in-list code blocks display correctly with highlighting.
  - Add the Pygments syntax-highlighting colour theme (`dracula`, scoped to `.codehilite`) to the generated stylesheet. Code blocks were emitting token spans with no matching CSS, so they rendered monochrome.
  - Fix the custom table-of-contents styling never applying: the rules targeted `nav[data-toggle='toc']` but the element is `<nav id="toc">`, so they are now keyed on `#toc`.
  - Keep the sticky table of contents below the navbar (offset + higher navbar `z-index`) so it no longer slides over the menu when scrolling.
  - Fix the 404 on the CI Workflows page on GitHub Pages. `actions/upload-pages-artifact` strips `.git`/`.github` from the deployed tarball, so the page generated under `public/.github/workflows/README.md/` was never published. It is now published under `public/github/workflows/README.md/` (leading dot dropped), with the site nav (`gen_pages.py`) and README updated to match.
- **Docs**:
  - Annotate the code fences in `dist/arch/install.md` with languages (`sh`, `text`, `ini`) so they get syntax highlighting, and wrap the previously unfenced shell snippet in the Sound section in a fenced block.
- **Neovim**:
  - Fix the treesitter highlighter crashing on Markdown (`README.md`) under Neovim 0.12: `Decoration provider "start" … attempt to call method 'range' (a nil value)`. The pinned nvim-treesitter `master` branch is frozen at Neovim 0.10/0.11 support; migrate `treesitter.lua` to the `main` branch (`require('nvim-treesitter').install()` + `vim.treesitter.start()` via a `FileType` autocmd) which supports Neovim 0.12, restoring Markdown highlighting.

## [v5.4.0](https://gitlab.com/pad92/dotfiles/-/releases/v5.4.0)

### Added

- **CI / Pages**:
  - Add a `post-commit` hook (via `pre-commit`) that regenerates the local `public/` documentation preview after each commit, backed by a reusable `.ci_bin/build_pages.sh` script also usable in CI.

### Changed

- **Hyprland**:
  - Increase animation speeds for windows, borders, fades, and workspaces for snappier UI transitions, and remove unused `borderangle` animation.
  - Tone down blur and shadow effects: reduce blur passes, disable opacity ignore and xray, and lower shadow range and render power.
  - Cap ASUS XG32WCS monitor at 60 Hz for productivity use on PadsP5560.
  - Remove hardware cursor override from PadsP5560 host config (use global default).
  - Simplify window rules: remove legacy KeePassXC, Bitwarden, and Dolphin rules, keep only Proton Pass for password manager.
  - Trim blur layer rules to `logout_dialog` only, removing unused swaync entries.
  - Launch `hyprlauncher` in daemon mode (`-d`) at autostart for instant toggle via keybind.
  - Simplify Lua configuration: merge `layout.lua` into `appearance.lua`, inline `utils.lua` helpers, delete empty `workspaces.lua`, and remove verbose comment banners across all files (~75% noise reduction).
  - Simplify the logout command to `pkill wlogout || wlogout` by removing the dead Quickshell (`qs`/`$qsConfig`) branch, since Quickshell is not installed.
  - Remove the redundant `SUPER+SHIFT+F` float-toggle binding (kept on `SUPER+ALT+Space`).
- **Hyprlock**:
  - Reduce playerctl widget update frequency from 1s/2s to 3s/5s to lower lock screen resource usage.
- **PipeWire**:
  - Enable WebRTC voice activity detection (VAD) and lazy activation (`node.passive`) on echo-cancel module to reduce CPU usage when mic is idle.
  - Compact voice effects configuration, removing redundant comments and whitespace.
- **Waybar**:
  - Split config into per-host files (`config.PadsTower`, `config.PadsP5560`). Desktop omits battery, backlight, and Intel temperature modules.
  - Remove unused weather module (`custom/weather`) configuration.
  - Remove the unused `#custom-weather` CSS selector.
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
  - Make the generated documentation pages responsive: wide tables now scroll horizontally on small screens instead of overflowing the layout, with adapted heading sizes and container padding on mobile; widen the main content block to the standard Bootstrap `1140px` container; remove a stray non-project comment block from `style.css`.
  - Minify the generated HTML and the copied `style.css` in `gen_pages.py`: collapse inter-tag whitespace (preserving `<pre>`/`<code>`/`<script>` content) and strip CSS comments/whitespace (~36% smaller CSS); drop the now-unused `shutil` import.

### Removed

- **neofetch**:
  - Remove deprecated neofetch configuration (743 lines), replaced by fastfetch.
- **ashell**, **noctalia**:
  - Remove empty unused configuration directories.
- **Alacritty**:
  - Remove stale base16 auto-backup file.
- **Submodules**:
  - Prune five stale `.gitmodules` entries from the i3/X11 setup, including `zsh-notify`, `i3blocks-contrib`, `gruvbox-rofi`, and `base16-alacritty`.
- **X11**:
  - Remove vestigial `.Xresources` and `.screenrc` (byobu/screen) leftovers on the all-Wayland setup.
- **Hyprland**:
  - Remove the orphan `hyprpaper.conf` (wallpapers are handled by `awww`).
- **Waybar**:
  - Remove three unused Waybar scripts, including `modules/headsetcontrol` and `modules/mediaplayer.py`. The inline `exec` in `audio.json` replaces `headsetcontrol`.
  - Remove the unused `network` module config from `conf/network.json` and its CSS: it duplicated the `nm-applet` tray indicator.

## [v5.3.2](https://gitlab.com/pad92/dotfiles/-/releases/v5.3.2)

### Added

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

### Changed

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
  - Set the `headsetcontrol` shebang to `bash`.
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

### Removed

- **Wofi**:
  - Clean up and remove all wofi configuration files (`.config/wofi`) and package installer entries.
- **Kanshi**:
  - Remove legacy Sway/Kanshi monitor profile configuration (`.config/kanshi/config`).
- **Systemd**:
  - Remove legacy X11 `xautolock.service` unit file.
- **Wlogout**:
  - Remove unused icon assets (`hibernate-hover1.png`, `moon_865813.png`, `sleep2.png`).

## [v5.3.1](https://gitlab.com/pad92/dotfiles/-/releases/v5.3.1)

### Added

- **Backup Utility**:
  - Introduce remote disk space delta calculation and log file size changes upon backup completion.
- **Installer**:
  - Add post-installation hook (`apply_live_changes`) to dynamically rebuild font cache, reload X resources (`xrdb`), and refresh desktop environments (Mako, Waybar).

### Changed

- **System Fonts**:
  - Standardize system-wide body and desktop environment UI fonts (GTK, Hyprland, Mako, wlogout, wofi) to **DejaVu Sans** and terminal/code blocks to **JetBrainsMono Nerd Font**.
- **Hyprland**:
  - Unify and centralize font and cursor configurations using dynamic Lua variables in compositor configurations.
- **Backup Utility**:
  - Refactor `backup.sh` to query loaded keys via `ssh-agent` rather than relying on hardcoded private key paths, exclude Lutris runner files, prune deprecated `.localised` exclude pattern, and translate logs from French to English.

### Removed

- **Legacy OS Support**:
  - Drop Ubuntu-specific bootstrap installer script (`dist/ubuntu/install.sh`) and related documentation.
- **Zsh & Utilities**:
  - Remove deprecated `command-not-found` shell plugin and its assets from `.zshrc` and plugin directory.

## [v5.3.0](https://gitlab.com/pad92/dotfiles/-/releases/v5.3.0)

### Added

- **Security & Passwords**:
  - Migrate from 1Password to **Proton Pass** as the default password manager.
  - Add `proton-pass-ssh-agent.service` systemd user service to manage the Proton Pass SSH agent.
  - Add `pass-cli` Zsh autocomplete plugin.
  - Add a centralized SSH agent initialization script (`zsh/init/ssh-agent.zsh`) to automatically detect and export the active SSH socket.
- **Zsh & Utilities**:
  - Add a custom `ssh-copy-agent-keys` function in `zsh/functions/ssh.zsh` to interactively select public keys loaded in the local `ssh-agent` and copy them to a remote server while avoiding duplicates.
- **Neovim & Editors**:
  - Build a modular Lua configuration for Neovim with `lazy.nvim`, Telescope, Treesitter, and Lualine.
- **Hyprland & Display**:
  - Refactor monitor/workspace setups to host-specific modular configurations (`hosts/PadsTower.lua`, `hosts/PadsP5560.lua`), update keybindings, and enable tearing support for low-latency gaming.
- **UWSM & Session Startup**:
  - Integrate UWSM for session management, centralize environment variables, and document systemd startup/GNOME Keyring PAM setup in the Arch Linux install guide.
- **Audio & Services**:
  - Implement a `shelly-notifications` user service, migrate Bluetooth configuration to Wireplumber (`50-bluez-config.conf`), and improve `awww` service reliability with dynamic Wayland socket checks.
- **CI/CD & Docs**:
  - Implement GitHub Actions pipelines for pages deployment/Vim packaging, and add an automated page generator (`gen_pages.py`) with table of contents support.

### Changed

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

### Removed

- **Legacy Components**:
  - Remove legacy `1password` Zsh plugin, including the helper function `opswd`.
  - Remove legacy `~/.xinitrc` configuration and its installer symlink.
  - Remove GDM display manager, old `kitty` theme configuration files, legacy helper scripts (`SystemControl.sh`, `power-profiles`, `xrandr.sh`), and the precompiled `greenclip-v4.2` binary.
- **Redundant Configs**:
  - Streamline environments by removing obsolete GNOME Keyring/SSH socket environment variables.

### Fixed

- **Compositor & Display**:
  - Resolve Gamescope mouse containment issues on multi-monitor setups using software rendering (`no_hardware_cursors = true`).
- **Drivers & Stability**:
  - Fix AMD RADV driver stability, refresh rate detection in `steam-optimize`, and correct QT QPA platform separator format compatibility.
- **Sandbox**:
  - Correct Electron feature flags and sandbox configurations.

## [v5.2.1](https://gitlab.com/pad92/dotfiles/-/releases/v5.2.1)

### Changed

- **Status Bar & Packages**:
  - Clean up Waybar configuration by removing unused modules, and consolidate essential package lists (Alacritty, GNOME utilities) into `11_hyprland.txt` and `20_apps.txt`.
- **Documentation**:
  - Update installation guide package paths and README.md to reflect archiving of legacy setups.

### Removed

- **Legacy Configs**:
  - Archive legacy X11, Sway, and Dunst configurations to `.config-archive/`, and prune obsolete package lists, old package diffs, screenshots, and Nitrogen setup instructions.

### Fixed

- **Electron**:
  - Fix Chromium/Chrome electron flags by properly combining multiple `--enable-features` onto a single line.

## [v5.2.0](https://gitlab.com/pad92/dotfiles/-/releases/v5.2.0)

### Added

- **Hyprland Upgrades**:
  - Upgrade Hyprland configuration to 0.55, introduce a centralized configuration module, define standard coding guidelines, and set default workspaces.
- **Gaming & Keybindings**:
  - Add custom Doom (2016) optimizations and Gamescope fixes in `steam-optimize`, and enhance shortcut bindings for screenshots, lock, and session controls.

### Changed

- **Desktop Daemons**:
  - Migrate wallpaper daemon from swww to awww, switch notification system from Dunst to Mako, and refine Hyprland animations/autostart.
- **Refactoring**:
  - Rewrite system backup utility to POSIX shell with improved rsync arguments, and optimize `steam-optimize` with helper functions.

### Fixed

- **Stability**:
  - Resolve fullscreen blackscreen issues and restore Steam overlay functionality.

## [v5.1.1](https://gitlab.com/pad92/dotfiles/-/releases/v5.1.1)

### Added

- **Arch & System**:
  - Add native Gamemode support, integrate firmware updates into the arch upgrade function, and add vimdiff instructions for `.pacnew` files.
- **Hyprland**:
  - Add initial host-specific configuration override support.

### Changed

- **CI & Aliases**:
  - Optimize pre-commit hooks to respect `.editorconfig` settings, enhance pre-commit leak detection, and refine shell alias error checking/validation.
- **Docs & Packages**:
  - Update Arch installation guide with modern practices (archinstall) and refresh the applications package list.

## [v5.1.0](https://gitlab.com/pad92/dotfiles/-/releases/v5.1.0)

### Added

- **Features**:
  - Implement automated changelog generation, add wlogout configuration, expand package manager utilities, and support newer Hyprland features.

### Changed

- **Aesthetics & UI**:
  - Refine Waybar status layouts, keybindings, fonts, system themes, and add missing system fonts.
- **Backup & Editor**:
  - Update VS Code extension lists and configure backup scripts to ignore WebStorage directories.

### Fixed

- **Status & Wallpaper**:
  - Fix temperature display, network formatting, wallpaper rotation rules, and DST-related bugs in status bars.
- **System**:
  - Fix Electron flags and resolve package installation inconsistencies.

## [v5.0.0](https://gitlab.com/pad92/dotfiles/-/releases/v5.0.0)

> Entries from here down to v1.0 are retrospective summaries reconstructed
> after the fact, not detailed at release time: expect them to be broader
> and less specific than v5.1.0 onward.

### Changed

- **Compositor Sync**:
  - Major overhaul and synchronization of Hyprland, Sway, and Waybar configurations.

## [v4.4.1](https://gitlab.com/pad92/dotfiles/-/releases/v4.4.1)

### Changed

- **Themes & Packages**:
  - Update visual themes, system color schemes, and package management helpers.

### Fixed

- **Status Bar**:
  - Correct Waybar temperature readings and network status formatting bugs.

## [v4.4.0](https://gitlab.com/pad92/dotfiles/-/releases/v4.4.0)

### Added

- **Compositor & UI**:
  - Introduce new Hyprland configuration options, add new status bar modules, and enhance package installation scripts.

### Changed

- **Keybinds & Fonts**:
  - Update config files, modernize keyboard shortcuts, and refine typography.

## [v4.3.0](https://gitlab.com/pad92/dotfiles/-/releases/v4.3.0)

### Added

- **Desktop Environments**:
  - Support new Hyprland features, enhance dual i3/Sway configurations, and improve package management wrappers.

### Changed

- **Structure**:
  - Refactor layout organization, update module setups, and simplify the installation flow.

## [v4.2.1](https://gitlab.com/pad92/dotfiles/-/releases/v4.2.1)

### Fixed

- **Stability**:
  - Resolve core stability issues, fix status bar layout bugs, and correct package installation mismatches.

## [v4.2](https://gitlab.com/pad92/dotfiles/-/releases/v4.2)

### Added

- **Structure**:
  - Add new configuration templates, optimize package management systems, and expand documentation.

### Changed

- **Architectural Overhaul**:
  - Restructure file layouts, update system dependencies, and rewrite installer scripts.

## [v4.1](https://gitlab.com/pad92/dotfiles/-/releases/v4.1)

### Added

- **Visuals**:
  - Add new themes, layout configurations, and improve package installation helpers.

### Changed

- **Polish**:
  - Refine keybindings, status bar modules, and enhance overall stability.

## [v4.0](https://gitlab.com/pad92/dotfiles/-/releases/v4.0)

### Added

- **Multi-Compositor**:
  - Complete overhaul of the configuration system, adding initial Hyprland support alongside modernized Sway and i3 setups.

### Changed

- **Architecture**:
  - Redesign file structures and update configurations to support latest upstream software versions.

## [v3.0](https://gitlab.com/pad92/dotfiles/-/releases/v3.0)

### Added

- **Multi-Desktop Setup**:
  - Introduce Sway alongside i3, and add clipboard (Greenclip), automounting (udiskie), and notification (Mako/twmn) daemons.
- **macOS Support**:
  - Add a Homebrew-based bootstrap with dedicated package lists and iTerm2/Atom configuration.
- **Terminal & Editors**:
  - Add Kitty and Alacritty terminal configurations, a Vim plugin bundle (Vundle), and expanded Zsh completions/notifications.
- **Tmux**:
  - Migrate to TPM, add a solarized theme, and mouse scroll/copy-paste support.

### Changed

- **Desktop Environment**:
  - Iterate through compositor (compton → picom) and terminal (Kitty → Alacritty) choices, switch to a base16/gruvbox color scheme, and rework the i3/Sway status bars (i3blocks, py3status, waybar backlight).
- **Configuration**:
  - Merge in the previously separate Manjaro-specific configuration.

### Removed

- **Terminal**:
  - Prune the superseded Kitty configuration and unused submodules after settling on Alacritty.

## [v2.1](https://gitlab.com/pad92/dotfiles/-/releases/v2.1)

### Added

- **Templates**:
  - Add additional package configs, visual themes, and package management helpers.

### Changed

- **Consistency**:
  - Refine status bar layouts, improve installer script reliability, and standardize settings.

## [v2.0](https://gitlab.com/pad92/dotfiles/-/releases/v2.0)

### Added

- **Visuals**:
  - Add window transparency support and initial setup templates.

### Changed

- **Cleanup**:
  - Reorganize system modules, update core keybinds, and clean up initial files.

## [v1.0](https://gitlab.com/pad92/dotfiles/-/releases/v1.0)

### Added

- **Initial Release**:
  - Core Zsh configurations, visual themes, and baseline system utilities.
