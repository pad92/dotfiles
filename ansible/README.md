# Ansible setup

Install `ansible-playbook` before using this setup. `./install` is a thin
launcher for the local playbook. Arguments pass straight through to
`ansible-playbook`:

```sh
./install --ask-become-pass
```

The playbook supports Arch Linux and CachyOS, Debian and Ubuntu, and Fedora. It
installs selected package groups, copies static dotfiles, renders host-aware
templates, links the Vim, tmux, and Zsh source trees, initializes Git submodules
at the revisions recorded by the repository, selects a Waybar configuration
matching the hostname, reloads live configuration, and configures makepkg for
local CPU builds on Arch Linux and CachyOS without generating separate debug
packages. Packages built with native CPU flags may not run on a different CPU.
Vim plugin updates are opt-in with `-e dotfiles_update_vim_plugins=true`.

Run `./install --tags makepkg --ask-become-pass` to configure makepkg without
running the other setup tasks. The existing `makepkg_config` tag remains
available as an alias.

The `ssh_client_hardening` tag hashes host names when the system SSH client
adds new entries to `known_hosts`. Existing entries are not converted. It does
not change the SSH server configuration.

The `kernel_hardening` tag manages `/etc/sysctl.d/hardening.conf` and saves a
timestamped backup before replacing it. The policy keeps the filesystem
protections, ASLR, ptrace and kernel-address restrictions, Docker forwarding,
inotify and file limits. It uses loose reverse-path filtering for asymmetric
VPN routes, disables shared-media redirects, and keeps IPv6 enabled by default
so LAN and VPN interfaces can configure it. Set
`system_ipv6_enabled_by_hostname` in `host_vars` to override the policy per
machine. The current inventory keeps
IPv6 enabled on `PadsTower` and disables it on `PadsP5560`. Disabling IPv6 sets
the `all` and `default` sysctls so existing and future interfaces follow the
host policy.

When `21_steam` is selected, the role adds the gaming sysctls to
`hardening.conf`, including `vm.max_map_count = 2147483642`. It backs up the
old `80-gamecompatibility.conf` and `99-cachyos-gaming.conf` files as
`<filename>.dotfiles-backup` before removing them. If that backup already
exists, Ansible keeps a timestamped copy before replacing it.

Ansible leaves `vm.mmap_rnd_bits` at `32` only when that value is already
active, since some supported kernels reject it. The role writes the
user-namespace setting only when the kernel exposes it. It sets
`net.core.bpf_jit_harden` to `2` when available, and persists unprivileged BPF
as the reversible value `2` in `/etc/sysctl.d/zz-dotfiles-bpf.conf`. The role
also applies that BPF setting immediately when its active value is `0`; a
running kernel already locked at `1` keeps that value until reboot.

The migration removes `kernel.kexec_load_disabled=1`, which cannot be undone
until reboot, and leaves TCP timestamps enabled with their randomized offsets.
It also drops interface-specific IPv6 overrides, which did not apply safely to
all desktop hosts. Reboot once after the migration to clear these old runtime
settings. Ansible does not reboot the workstation.

Run either tag with `./install --tags ssh_client_hardening --ask-become-pass`
or `./install --tags kernel_hardening --ask-become-pass`.

### AMD CPU performance

The `amd_cpu_performance` tag uses the CPU vendor from Ansible facts and the
controls exposed by the kernel. With AMD P-State in active mode, it selects
`powersave` before applying `system_amd_pstate_epp` (default:
`balance_performance`). Both values must be available on the CPU policy.
Here, `powersave` lets EPP guide the CPU's performance and energy use.

Ansible skips direct EPP changes while a known power manager is active or
enabled (`power-profiles-daemon`, auto-cpufreq, TLP, or tuned). This preserves
the manager's selected profile, including a game's temporary performance profile.
Set `system_amd_pstate_epp: null` to disable direct EPP management entirely.

The X3D CCD mode stays unchanged unless `system_amd_x3d_mode` is set to `cache`
or `frequency` and the kernel exposes the AMD X3D control. Choose the mode for
the workloads of the target machine. Ansible does not change Core Performance
Boost or the kernel boot parameters.

Apply the runtime settings with:

```sh
./install --tags amd_cpu_performance --ask-become-pass
```

These writes are not persisted across reboot. See the
[CachyOS CPU tuning guide](https://wiki.cachyos.org/fr/configuration/general_system_tweaks/)
for firmware requirements and the effect of power profiles.

### Gaming

The `21_steam` group selects Steam, Gamescope, MangoHud, `ananicy-cpp`,
`power-profiles-daemon`, and `python-gobject` on Arch Linux and CachyOS. On
CachyOS, it also selects Proton CachyOS SLR, `cachyos-ananicy-rules`, and
`cachyos-settings`, which provides `game-performance`. These CachyOS packages
are added only when Ansible facts identify the distribution as CachyOS. Ansible
requires them to be available in configured CachyOS repositories instead of
trying to build them from the AUR. `cachyos-settings` also installs CachyOS
system defaults for sysctl, udev, and other components
([package documentation](https://wiki.cachyos.org/fr/features/cachyos_settings/)).

When `21_steam` is selected, Ansible enables and starts `ananicy-cpp` and
`power-profiles-daemon`. Configuration stops if auto-cpufreq, TLP, or tuned is
active or enabled. Resolve that conflict before rerunning the playbook. Once
the check passes, Ansible removes any systemd mask from
`power-profiles-daemon.service` before enabling it. An existing `ananicy-cpp`
service is kept running. The selected packages provide the rules and daemon
configuration.

To install the selected groups and configure gaming services, run:

```sh
./install --tags packages,gaming --ask-become-pass
```

The `gaming` tag alone configures services after checking that their packages
are installed. It uses the usual package group selection; it does not select
`21_steam` automatically. Deselecting Steam does not stop existing services.
GameMode is excluded from the package list. An already installed copy is only
eligible for removal through `packages_action=reconcile` if Ansible owns it.

The `lact` tag manages `/etc/lact/config.yaml` when `lactd.service` is installed.
It reads the exact GPU identifiers and drivers from LACT, then creates missing
`Balance`, `Silence` and `Jeux-perf` profiles for detected AMD GPUs. New profiles
keep automatic fan control; `Balance` and `Silence` use automatic performance
levels, while `Jeux-perf` uses `high`. Customize the fan curves in LACT as needed.
Existing profile settings, automation and profile selection are preserved.
Identifier casing is repaired, but an unknown GPU or conflicting entries stop
the deployment before the configuration is written. A symlink or directory at
`system_lact_config_path` is also refused; select the intended regular file
explicitly instead. Changes receive a backup
and restart `lactd`.

```sh
./install --tags lact --ask-become-pass
```

`--check` requires an already running LACT daemon for discovery. The legacy
`~/.config/lact/config.yaml` is left untouched and is no longer deployed.
With LACT 0.7.5+ and PPD 0.30+, LACT disables PPD's conflicting `amdgpu_dpm`
action automatically ([LACT documentation](https://github.com/ilya-zlobintsev/LACT#power-profiles-daemon-note)).
Check `powerprofilesctl list-actions` and `journalctl -u lactd -b` after deployment.

The group's sysctl policy raises `vm.max_map_count` for Proton games during a
full run or with `--tags kernel_hardening`. The `steam-optimize` launcher uses
`game-performance` on CachyOS; on Arch Linux it launches without that CachyOS
profile manager. It sets a 12 GB Mesa shader cache for AMD or
a 12 GB proprietary-driver cache for NVIDIA; game profiles can override those
values. Arc Raiders uses a 20 GB Mesa cache.

To select the Steam account configuration, `steam-optimize` first reads the
most recently used account from `loginusers.vdf`. If that account cannot be
matched to a local configuration, it uses the sole `localconfig.vdf` when
exactly one exists. With multiple configurations and no match, it leaves the
account selection unresolved.

Avoid adding `gamemoderun` while `ananicy-cpp` is active: both can change process
priorities ([CachyOS gaming guide](https://wiki.cachyos.org/fr/configuration/gaming/)).
`ENABLE_LAYER_MESA_ANTI_LAG` remains a per-game option because compatibility
varies between games.

Package groups start with the OS-family file in `roles/packages/vars/`. The
package role then loads the first matching exact-version, major-version, or
distribution override. Selection, installation, and reconciliation stay in
separate task files.

On Arch Linux and CachyOS, the package role sets `Color`, `ILoveCandy`, and
`CheckSpace`, enables the standard `multilib` repository, and sets
`ParallelDownloads = 5` in `/etc/pacman.conf`. On CachyOS, it also enables
`PrettyProgressBar`. Enabling `multilib` triggers `pacman -Syu`,
which synchronizes package databases and upgrades installed packages. Use
`-e packages_upgrade_system=true` to request a full system upgrade whenever
packages are installed, including when `multilib` is already enabled.

Selected AUR packages are installed with `yay`. If it is missing, the role
clones its AUR recipe, builds it as the current user, then installs the package
with Ansible privilege escalation. Set `-e packages_aur_action=ask` to confirm
AUR builds and installations, or `-e packages_aur_action=skip` to leave AUR
packages uninstalled.
Run `./install --tags yay --ask-become-pass` to run the package selection and
AUR installation flow without installing the selected official repository
packages.

Package groups are selected automatically from OS defaults and detected GPU
facts. Configure exact selections by hostname in `host_vars/localhost.yml`; those
lists replace the defaults. `packages_group_selection` remains available as a
one-run override. The default Vault password file is `.vault`, which is ignored
by Git. Create it locally when using Vault-encrypted content, or pass
`--vault-password-file` to override it. Example of a one-run package group
override:

```sh
./install --ask-become-pass \
  -e '{"packages_group_selection":["01_base","03_gtk"]}'
```

On Arch Linux, selecting an NVIDIA profile makes the system role manage
`/etc/modprobe.d/zz-dotfiles-gpu.conf`. Both profiles enable zero-initialized
system memory and DRM modesetting. The modern profile also enables NVIDIA's
coarse-grained runtime D3 power management; the legacy profile does not, since
NVIDIA documents RTD3 support for Turing and newer GPUs. Open kernel modules
preserve video memory automatically. The role does not force that behavior on
the proprietary legacy driver, which would require systemd integration and
adequate temporary storage.

When either NVIDIA profile is selected, Ansible detects `mkinitcpio` or
`dracut` and regenerates the initramfs after the module configuration changes.
If both or neither are installed, set `system_initramfs_generator` to
`mkinitcpio` or `dracut`. GSP firmware is enabled by default on supported GPUs,
so Ansible does not set it. The i915 GuC option remains at the kernel default,
matching the commented local setting. To configure it for the modern Intel
profile, set `system_i915_enable_guc` to `-1`, `0`, `1`, `2`, or `3`; `-1`
keeps automatic selection, while `1` enables GuC submission and `2` enables
HuC authentication; `3` enables both. The kernel documents these features and
notes that support varies by platform. Values `1`, `2`, and `3` also require
`system_i915_guc_supported: true`, which must only be set after confirming the
GPU supports the selected operation. See NVIDIA's [runtime D3 documentation](https://download.nvidia.com/XFree86/Linux-x86_64/615.78.08/README/dynamicpowermanagement.html),
[power management documentation](https://download.nvidia.com/XFree86/Linux-x86_64/615.78.08/README/powermanagement.html),
and the kernel's [i915 driver documentation](https://docs.kernel.org/gpu/i915.html).

Conflicting regular files and directories that need a type change are moved to
a `.bak` path. Existing symbolic links at managed paths are removed without a
backup; their targets are left untouched. Package installation is additive.
On Arch Linux, enabling `multilib` triggers a full `pacman -Syu`. Otherwise,
installing selected packages does not upgrade the whole system by default. Set
`-e packages_upgrade_system=true` to use `pacman -Syu` when installing missing
packages. Use `--check` to preview package changes and
`-e packages_action=reconcile` to enable explicit, ownership-based removals.
Use `--check --tags dotfiles` to preview dotfile link changes separately.

Use `make ansible-backup-ls` to list backups created for Ansible-managed
dotfiles, or `make ansible-backup-rm` to review and remove them after a
confirmation prompt. Both targets use `$HOME` by default; set
`ANSIBLE_BACKUP_ROOT=/path` on the `make` command line to select another root.
