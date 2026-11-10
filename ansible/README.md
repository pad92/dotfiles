# Ansible setup

Install `ansible-playbook` before using this setup. The `make install` target
runs the local playbook. Pass options through `ANSIBLE_ARGS`:

```sh
make install ANSIBLE_ARGS=--ask-become-pass
```

The playbook supports Arch Linux and CachyOS, Debian and Ubuntu, and Fedora. It
installs selected package groups, copies static dotfiles, renders host-aware
templates, links the Vim, tmux, and Zsh source trees, initializes Git submodules
at the revisions recorded by the repository, selects a Waybar configuration
matching the hostname, reloads live configuration, and configures makepkg for
local CPU builds on Arch Linux and CachyOS without generating separate debug
packages. Packages built with native CPU flags may not run on a different CPU.
Vim plugin updates are opt-in with `-e dotfiles_update_vim_plugins=true`.
Dotfile copies, templates, backups, and removals use Ansible file modules.
Directory deployments show each changed file. Custom modules report files
written by sysfs controls, submodule updates, package builds, and initramfs
generation. Conflict backups use an atomic move that refuses existing targets.
AUR installation uses a dedicated module for yay/paru, without Pacman's
unsupported `--print-format` calls.

The yay bootstrap keeps makepkg's package, source, build and log destinations
inside its temporary build tree. Initramfs reporting inventories
`system_initramfs_report_roots` (default: `/boot`, `/efi`). Add any custom image
or hook output directories, including targets outside those trees, to this list.
Unreadable inventory paths fail the task instead of producing a partial success.
Package transaction internals and arbitrary external hooks are not a complete
filesystem audit; the reported paths cover the declared output trees.

Run `make install ANSIBLE_ARGS="--tags makepkg --ask-become-pass"` to configure makepkg without
running the other setup tasks. The existing `makepkg_config` tag remains
available as an alias.

The `ssh_client_hardening` tag hashes host names when the system SSH client
adds new entries to `known_hosts`. Existing entries are not converted. It does
not change the SSH server configuration.

The `kernel_hardening` tag manages `/etc/sysctl.d/60-dotfiles-hardening.conf`
and `/etc/sysctl.d/70-dotfiles-bpf.conf`. Their numeric prefixes place local
policy after package defaults in `/usr/lib/sysctl.d/`, following systemd's
recommended filename ordering. The role backs up its former drop-ins before
removing them. The policy keeps the filesystem
protections, ASLR, ptrace and kernel-address restrictions, and inotify limits.
IPv4 forwarding is enabled only when `12_containers_docker` or
`13_containers_podman` is selected, and disabled otherwise. It uses loose reverse-path filtering for asymmetric
VPN routes, disables shared-media redirects, and keeps IPv6 enabled by default
so LAN and VPN interfaces can configure it. Set `system_ipv6_enabled: false`
in a host's settings file (see [Per-host settings](#per-host-settings)) to
disable it on that machine. `PadsP5560` disables IPv6 and `PadsTower` keeps it. Disabling IPv6 sets
the `all` and `default` sysctls so existing and future interfaces follow the
host policy.

When `21_steam` is selected, the role adds
`vm.max_map_count = 2147483642` to `60-dotfiles-hardening.conf`. Proton documents this
value for games that need more mappings than the kernel default. The role backs
up the old `80-gamecompatibility.conf` and `99-cachyos-gaming.conf` files as
`<filename>.dotfiles-backup` before removing them. If that backup already
exists, Ansible keeps a timestamped copy before replacing it.

The gaming policy leaves swappiness, dirty page writeback, scheduler behavior,
network backlog, file-handle limits, and compatibility-mode mmap randomization
at their kernel or distribution defaults. These settings are not required for
Proton and can affect general desktop workloads.

Ansible leaves `vm.mmap_rnd_bits` at `32` only when that value is already
active, since some supported kernels reject it. The role writes the
user-namespace setting only when the kernel exposes it. It sets
`net.core.bpf_jit_harden` to `2` when available, and persists unprivileged BPF
as the reversible value `2` in `/etc/sysctl.d/70-dotfiles-bpf.conf`. The role
also applies that BPF setting immediately when its active value is `0`; a
running kernel already locked at `1` keeps that value until reboot.

The migration removes `kernel.kexec_load_disabled=1`, which cannot be undone
until reboot, and leaves TCP timestamps enabled with their randomized offsets.
It also drops interface-specific IPv6 overrides, which did not apply safely to
all desktop hosts. Reboot once after the migration to clear these old runtime
settings. Ansible does not reboot the workstation.

Run either tag with `make install ANSIBLE_ARGS="--tags ssh_client_hardening --ask-become-pass"`
or `make install ANSIBLE_ARGS="--tags kernel_hardening --ask-become-pass"`.

### Per-host settings

The inventory has a single `localhost` host. At the start of `site.yml` and
`obs.yml`, a `group_by` task adds it to the group `host_<hostname>`, using
the hostname fact; characters other than letters, digits and `_` become `_`.
Ansible then loads `ansible/group_vars/host_<hostname>.yml` on top of
`ansible/group_vars/all/`. A machine without such a file keeps the role
defaults: OS and GPU package groups, IPv6 on, hypridle on.

`group_vars/all/packages.yml` defines `packages_workstation_groups`, the
groups both workstations share. Each host file builds its list from it:

```yaml
# ansible/group_vars/host_PadsP5560.yml
packages_host_groups: "{{ packages_workstation_groups + ['23_vpn'] }}"
system_ipv6_enabled: false
dotfiles_hypridle_enabled: false
```

To add a machine, create `ansible/group_vars/host_<hostname>.yml` with the
output of `hostname -s`. `packages_host_groups` is a list; the packages role
rejects any other type. A `-e` option still overrides any of these settings
for one run.

### DNS

The `dns` tag makes systemd-resolved the only DNS resolver. NetworkManager
hands it each link's servers (`/etc/NetworkManager/conf.d/60-dotfiles-dns.conf`),
and `/etc/systemd/resolved.conf.d/60-dotfiles-dns.conf` sets the policy:

- `LLMNR=no` (`system_dns_llmnr`). A single-label name that DNS cannot resolve
  is never asked on the local network, where any host could answer it.
- `MulticastDNS=resolve` (`system_dns_multicast_dns`). `.local` names still
  resolve, but the host does not announce its name.
- An empty `FallbackDNS=` (`system_dns_fallback_servers`). When no link has DNS
  servers, lookups fail instead of going to the compiled-in public resolvers in
  clear text. List servers there to keep a fallback.

The tag needs `systemd-resolved.service`, a running `NetworkManager.service`
and `nmcli`. When one of them is missing, the role says which and skips the DNS
policy without changing anything. Set `system_dns_manage: false` in the
host's settings file (see [Per-host settings](#per-host-settings)) to leave
the resolver alone on every run,
including full runs, for example after
[undoing the migration](../dist/arch/dns-migration.md#5-undo-the-migration).

Hosts installed with the earlier openresolv setup, with or without a dnsmasq
relay added by hand, are migrated by the same tag. The
[DNS migration note](../dist/arch/dns-migration.md) gives the procedure; this
section describes the rules it relies on.

#### Docker

With `12_containers_docker`, resolved also listens on the Docker bridge address
(`system_docker_bridge_ip`, default `10.184.1.1/28`). The role sets it as `bip`
and as the only `dns` entry in `/etc/docker/daemon.json`, and keeps the other
keys. Containers then get the host's view, including VPN split DNS. The
listener binds even while `docker0` is absent.

Docker reads the file at startup, so restart `docker.service` yourself when no
container needs to stay up. Without an earlier `bip`, Docker used
`172.17.0.1/16`: containers on the default bridge get new addresses, and the
new network must not overlap a LAN or VPN route of the host.

A `/28` leaves 13 addresses for containers on the default bridge, after the
network, broadcast and bridge addresses. User-defined networks take their
subnets from `default-address-pools`, not from `bip`. A `fixed-cidr` inside
the bridge network is kept. One outside it makes the play fail, because Docker
would refuse to start; change `fixed-cidr` or `system_docker_bridge_ip`. An
empty `daemon.json` is read as `{}`.

Before changing anything, the role lists the port 53 listeners with `ss`. If a
program other than resolved, or the relay dnsmasq it is about to stop, holds
port 53 on the bridge address or on all addresses, the play stops and names
it, and that program keeps running. The relay is recognised by the main pid of
`dnsmasq.service`, so any other dnsmasq on all addresses stops the play too.
libvirt's dnsmasq listens on its own bridge addresses and does not conflict.

After the `resolv.conf` switch, the role lists the listeners again and fails
if resolved does not hold port 53 on the bridge address over both UDP and TCP.
resolved only logs a listener it cannot bind, so this is what keeps
`daemon.json` from pointing containers at an address nothing answers on. Check
mode skips this, since it does not restart resolved.

Removing `12_containers_docker` later drops the listener but leaves `bip` and
`dns` in `daemon.json`. Containers then query an address nothing answers on, so
remove the `dns` entry yourself if Docker stays installed.

#### resolv.conf

The role enables and starts `systemd-resolved.service`, then links
`/etc/resolv.conf` (`system_dns_resolv_conf`) to
`/run/systemd/resolve/stub-resolv.conf`. A link that already resolves to the
stub, relative or not, is left alone. A link to another file, including
`/run/systemd/resolve/resolv.conf`, is replaced: that file sends programs
straight to the upstream servers and skips the stub, so the resolved policy
would not apply to them.

A regular `resolv.conf` is replaced only when this policy supersedes its
writer. That is the case when it has an openresolv, NetworkManager or
systemd-resolved header, or when all its name servers are loopback addresses
(the former relay, or a stale copy of the stub). A VPN client can restore such
a copy after disconnecting, and the next run links it again.

Any other regular file is left alone, and the play prints its first comment
line. This is typically a VPN client that rewrote the file while connected:
run the tag again after disconnecting. Set
`system_dns_force_resolv_conf_link` to `true` to replace it anyway.

If the stub file is missing once resolved has started, the play fails before
linking `resolv.conf`. NetworkManager may have been reloaded by then and may
have rewritten a regular `resolv.conf` itself. After the switch, the play runs
`resolvectl query localhost`, which needs no network, and fails if resolved
does not answer. The Docker settings are written last.

#### Former dnsmasq relay

The relay is recognised by the files in `system_dns_relay_files`. Only when one
of them exists does the role touch NetworkManager profiles and
`dnsmasq.service`. Without them, a loopback DNS server is treated as a
deliberate local resolver (unbound, dnscrypt-proxy) and left alone, and so is
`dnsmasq.service`.

With the relay present:

- A profile family whose DNS servers are all loopback addresses and whose
  method is automatic (`auto`, or `dhcp` for IPv6) goes back to DHCP DNS, and
  the play lists it. It is reapplied without reconnecting, except VPN, WireGuard and tun connections,
  which are listed so you can reconnect them.
- A family with another method (`manual`, `link-local`, `shared`) would have no
  server left, so it is reported and left unchanged. The report lists the
  `server=` lines of the relay files as candidates.
- Profiles that mix loopback and remote servers are reported and left
  unchanged. Profiles without IP settings, such as bridge ports, are skipped.
- The relay files are removed and `dnsmasq.service` is stopped and disabled.

The NetworkManager files in `system_dns_legacy_files` (`dns.conf`, and the
`rc-manager.conf` with `rc-manager=resolvconf` from the earlier install guide)
are removed when they set nothing but `dns=` or `rc-manager=` in `[main]`. A
file with other settings is kept and reported, since its DNS lines may still
override `dns=systemd-resolved`.

The role removes no package. openresolv came from the earlier install guide
and the relay's dnsmasq was added by hand, both outside the package lists, so
`packages_action=reconcile` does not see them either; the migration note
covers their removal.

#### Backups

Each file the role removes or replaces (relay files, legacy NetworkManager
files, a regular `resolv.conf`) is first copied under its full path to
`system_dns_backup_dir`, for example
`/var/lib/dotfiles/dns-backup/etc/resolv.conf`. The directory is readable by
root only and the copies have mode `0600`, so restore them with an explicit
mode rather than `cp -a`. When a later run backs up the same path again, the
earlier copy is kept as `<file>.<pid>.<date>~`, where `<date>` is the backup
time. Order copies by that date: their file times are those of the original
files. `daemon.json` gets a
timestamped copy next to it instead. NetworkManager profiles are not backed up.

#### Migration order

On a migrated host, resolved starts first, then the profiles change, dnsmasq
stops and the relay files are removed. dnsmasq stops before its files go,
because they are how the role recognises the relay: a run interrupted in
between can then still finish on the next run. resolved is restarted and NetworkManager reloaded right
after, and `resolv.conf` switches last. Lookups through the old `resolv.conf`
fail during the short window between the dnsmasq stop and the switch. resolved
is restarted rather than reloaded, because it binds extra listeners and drops
the compiled-in fallbacks only at startup.

Check mode reads profiles and files but changes nothing and creates no backup.
The play reports the profiles it moves to DHCP DNS in both modes, because
`ansible.cfg` hides the skipped `nmcli connection modify` items in check mode.

Run `make install ANSIBLE_ARGS="--tags dns --ask-become-pass"` to apply it
alone.

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
make install ANSIBLE_ARGS="--tags amd_cpu_performance --ask-become-pass"
```

Ansible also writes the settings it applied to
`/etc/tmpfiles.d/dotfiles-amd-cpu.conf` (`system_amd_tmpfiles_path`), so
`systemd-tmpfiles` restores them at boot: the `powersave` governor first, then the
EPP preference, then the X3D mode. EPP lines are only written while no power
manager is active or enabled. The file is removed when Ansible no longer manages
any of these controls. See the
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
`power-profiles-daemon`. If auto-cpufreq, TLP, tuned, or another known CPU
power manager is active or enabled, the playbook asks whether to stop, disable,
and uninstall it, and stops if you decline. Set
`-e system_power_manager_conflict_action=remove` to remove it without asking, or
`fail` to keep the old behavior. Check mode never removes anything. Once
the check passes, Ansible removes any systemd mask from
`power-profiles-daemon.service` before enabling it. An existing `ananicy-cpp`
service is kept running. The selected packages provide the rules and daemon
configuration.

To install the selected groups and configure gaming services, run:

```sh
make install ANSIBLE_ARGS="--tags packages,gaming --ask-become-pass"
```

The `gaming` tag alone configures services after checking that their packages
are installed. It uses the usual package group selection; it does not select
`21_steam` automatically. Deselecting Steam does not stop existing services.
GameMode is excluded from the package list. An already installed copy is only
eligible for removal through `packages_action=reconcile` if Ansible owns it.

The `lact` tag manages `/etc/lact/config.yaml` when `lactd.service` is installed.
It reads GPU identifiers and drivers from LACT, then creates missing `Auto`,
`Adaptive` and `PreferMaximumPerformance` profiles for AMD and NVIDIA GPUs.
These names match LACT's NVIDIA PowerMizer modes. AMD profiles use automatic
performance levels for `Auto` and `Adaptive`, then `high` for
`PreferMaximumPerformance`. NVIDIA profiles use the matching PowerMizer mode.
Profiles do not override fan control. Intel GPUs keep their existing settings.
Existing `Balance`, `Silence`, `Performance` and `Jeux-perf` profiles are
renamed and removed under their old names. Their settings move to the new name
when it is unused; an existing profile with the new name takes priority. The
current selection follows the rename. Defaults fill only missing GPU entries
in existing profiles. Other settings and automation are preserved.
When no named profile exists, `Auto` becomes active after the profiles are added.
Identifier casing is repaired; an unknown GPU or conflicting entries stop
deployment before the configuration is written. A symlink or directory at
`system_lact_config_path` is also refused. Changes are backed up and restart
`lactd`.

```sh
make install ANSIBLE_ARGS="--tags lact --ask-become-pass"
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
Run `make install ANSIBLE_ARGS="--tags yay --ask-become-pass"` to run the package selection and
AUR installation flow without installing the selected official repository
packages.

Package groups are selected automatically from OS defaults and detected GPU
facts. A machine with its own `packages_host_groups` list (see
[Per-host settings](#per-host-settings)) replaces those defaults.
`packages_group_selection` remains available as a one-run override. Vault is optional. When `.vault` (ignored by Git) exists, the
`make` targets export it as `ANSIBLE_VAULT_PASSWORD_FILE`. Set
`DOTFILES_VAULT_PASSWORD_FILE=/path` on the `make` command line to use another
file. A fresh clone without `.vault` runs without Vault. Example of a one-run package group
override:

```sh
make install ANSIBLE_ARGS="--ask-become-pass -e '{\"packages_group_selection\":[\"01_base\",\"03_gtk\"]}'"
```

On Arch Linux, selecting an NVIDIA profile makes the system role manage
`/etc/modprobe.d/zz-dotfiles-gpu.conf`. Both profiles enable zero-initialized
system memory and DRM modesetting. Runtime D3 uses the NVIDIA driver's default:
supported Ampere and newer notebooks use fine-grained power management.
Ansible installs a runtime PM udev rule only when sysfs reports a host battery,
an Intel or AMD boot VGA GPU, a separate NVIDIA GPU, and the modern
NVIDIA package profile is selected. The rule matches the bound driver and sets
PCI `power/control` to `auto`; it contains no device-specific identifiers.
When the rule changes, Ansible reloads the udev rules and replays a `bind`
event for PCI devices bound to `nvidia`, so the rule applies without a reboot.
Removing the rule leaves `power/control` at `auto` until the next reboot. Reboot
after deployment to apply the module configuration.
Peripheral batteries marked `Device` are excluded. If battery metadata or GPU
detection is incomplete, Ansible preserves the existing rule and reports that detection
must be retried after the drivers load. A first installation may therefore
require another run of the `gpu_modules` tasks after reboot.
Open kernel modules
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

UWSM discovers DRM cards at session startup and places the unique boot VGA
card first, followed by the remaining GPUs. The firmware's boot selection
does not establish whether a card is integrated or dedicated. If several GPUs
are present without a unique boot VGA card, UWSM leaves GPU selection unchanged
and prints a diagnostic so Aquamarine can use its default or an existing override.
The resulting Aquamarine device list uses the current DRM nodes without storing
card numbers or PCI addresses. If discovery finds no usable cards, UWSM leaves
GPU selection unchanged. This selection is evaluated at login; reconnect the
session after changing the GPU hardware.

Application driver selection remains automatic, including Vulkan and VA-API.
Use `prime-run application` for workloads that need NVIDIA. Remove any previous
session-wide `VK_DRIVER_FILES` override before testing offload. Keep LACT on
`Auto` for normal office use. After deployment and reboot, check idle runtime
suspension, application offload, external displays and suspend/resume. An active
GPU workload or a monitoring client can keep the NVIDIA device awake; runtime
PM configuration alone does not establish an autonomy improvement.

Conflicting regular files and directories that need a type change are moved to
a `.bak` path. Symbolic links at managed paths that point elsewhere are moved to
`.bak` the same way, so their targets stay recorded and untouched. Package installation is additive.
On Arch Linux, enabling `multilib` triggers a full `pacman -Syu`. Otherwise,
installing selected packages does not upgrade the whole system by default. Set
`-e packages_upgrade_system=true` to use `pacman -Syu` when installing missing
packages. On Arch Linux, a package counts as installed when an installed
package provides its name (`pacman -T`), for example `foo-git` for `foo`.
Use `--check` to preview package changes and
`-e packages_action=reconcile` to enable explicit, ownership-based removals.
Removals never touch the built-in base set (`base`, `glibc`, `pacman`, `systemd`,
`linux` and `linux-*`, and a few others) or the extra names listed in
`packages_protected`.
Use `--check --tags dotfiles` to preview dotfile link changes separately.

The `package_services` tag enables and starts the units of selected package
groups on Arch Linux (`system_package_services`): `bluetooth.service` with
`01_base`, `cups.socket` with `04_printers`,
`docker.socket` with `12_containers_docker`, and `fwupd-refresh.timer` with
`20_apps`. A unit whose file is missing is reported instead of enabled. With
`12_containers_docker`, the users in `system_docker_group_users` (default: the
user running `make install`) join the `docker` group, which grants
root-equivalent access to the Docker daemon; log in again to use it. When the
playbook installs or updates `cachyos-ananicy-rules`, it restarts `ananicy-cpp`
so the new rules load.

Use `make ansible-backup-ls` to list backups created for Ansible-managed
dotfiles, or `make ansible-backup-rm` to review and remove them through an
Ansible file task after a confirmation prompt. The helper script only collects
the candidate paths. Both targets use `$HOME` by default; set
`ANSIBLE_BACKUP_ROOT=/path` on the `make` command line to select another root.

### OBS

The `22_obs` group selects OBS Studio, the PipeWire Pulse server, WirePlumber,
the Hyprland portal backend, `qt6-wayland`, `v4l-utils`, `v4l2loopback-dkms`,
the `obs-backgroundremoval` plugin (built from the AUR), `simde`, and
`ttf-montserrat`. `simde` is a build requirement of every OBS 33 plugin that
the AUR recipe does not declare. The plugin's `onnxruntime` dependency takes any provider
already installed (CPU, CUDA or ROCm); the filter itself runs on the CPU. Both workstations select it through
`packages_workstation_groups`. To install OBS and
nothing else, use the standalone profile:

```sh
make install-obs ANSIBLE_ARGS=--ask-become-pass
```

`ansible/obs.yml` runs the `packages` role with `22_obs` plus the GPU groups
detected by `lspci`, then the `obs` role. It skips the `system` and `dotfiles`
roles and refuses `packages_action=reconcile`, which would treat every other
managed package as obsolete. Run a reconcile with `make install` instead. Any
selected `*-dkms` package also brings the headers of the running kernel; the
package that owns `/usr/lib/modules/<kernel>/vmlinuz` names them (for example
`linux-zen-headers`).

The `obs` role reads the host before writing anything:

- Encoder: the GPU that renders the desktop (`boot_vga`) encodes. A hybrid
  laptop uses VAAPI on its iGPU and the NVIDIA GPU stays asleep; a desktop
  whose screens hang off NVIDIA uses NVENC. A five-frame ffmpeg encode proves
  the choice, and x264 is used when it fails, with a preset sized to the CPU
  thread count. Force one with `obs_encoder=nvenc|vaapi|x264`.
- Video: the canvas is 16:9 at the native height of the largest external
  output from `hyprctl monitors` (`obs_capture_output` picks one), scaled with
  Lanczos to `obs_output_height` (1080). Frame rate is 60 with a hardware
  encoder on a 60 Hz screen, 30 otherwise. Without a Hyprland session the
  canvas falls back to 1920x1080.
- Webcam: every `/dev/video*` node is listed and only colour capture nodes
  (MJPG or YUYV) are kept, so infrared and metadata nodes are skipped. External
  cameras win over integrated ones (`obs_webcam` matches a name or path). The
  source uses the `/dev/v4l/by-id` link, else `by-path`, in MJPEG up to
  1280x720 at 30 fps: YUYV at 1080p drops to 5 fps on USB 2.
  Without a camera the scenes get no Caméra source, and the run warns: plug
  the webcam in and regenerate with `-e obs_config_force=true`.
- Recordings: hybrid MP4 in `$(xdg-user-dir VIDEOS)/OBS`.
- Webcam background: with `obs-backgroundremoval` installed, the default
  `obs_webcam_background=cutout` makes the background transparent so the
  person sits directly on the scene; the camera then has no accent frame and
  touches the bottom edge, so the shoulders leave the picture naturally.
  The default `obs_webcam_model=rvm` (Robust Video Matting) works at 320x192
  and remembers the previous frames. It outputs a soft alpha that follows
  hair, so the role leaves the plugin's threshold off. It runs on the CPU with
  four threads, or two below 8 threads, so the NVIDIA GPU stays asleep.
  `mediapipe` is lighter but segments at 256x144: on a 720p camera its mask
  shows stair-stepped edges and loses parts of the neck or keeps a chair arm.
  With it the mask is thresholded and leans towards hiding the room: a pixel
  stays the person only above `obs_webcam_threshold` (0.65, the plugin default
  is 0.5), and `obs_webcam_edge_trim` (2 pixels) trims the room's halo off the
  outline. The contour filter keeps the upstream 0.05, since a larger value
  merges small background areas, such as the gap under an arm, into the
  person. `blur` keeps a soft blurred background (`obs_webcam_blur`, 6 out of 20) in a framed inset, `none` keeps the raw picture. Unchanged frames and a
  hidden camera skip inference. The plugin is built against the installed OBS: rebuild it with
  yay after an OBS upgrade if OBS reports it as not loaded.

The scenes follow the brand guide: Montserrat, text #FFFFFF on #242428 in
the default dark theme (`obs_brand_theme=light` uses #2A3235 on #FFFFFF), and
the primary colour #41A890 for the title underline and the frame around the
camera. Titles need the static Montserrat weights from `ttf-montserrat`: OBS
opens the first face of a font file, which is the Thin instance of the variable
Montserrat shipped with Google Fonts. The run warns when no static Bold face
exists.

It creates the profile and the scene collection "Démo Applis" next to the
existing ones. Scenes: intro (title and camera), screen with a camera inset,
screen only, one application window on a backdrop with the camera, camera
only, and a pause card. Desktop audio and the microphone (`obs_mic_device`,
RNNoise unless `obs_mic_noise_suppression=false`) are global sources. Screen
and window captures go through the XDG portal: Wayland gives no way to name
the output in advance, so OBS asks once and keeps a restore token.

OBS rewrites these files when it exits, so the role creates them once and
then leaves them alone. Run with `-e obs_config_force=true` to regenerate them
from the current host; the previous files are kept as backups. The run refuses
to regenerate while OBS is open, since OBS would overwrite the files on exit.

The virtual camera serves Teams and other web meetings. The role writes
`/etc/modprobe.d/zz-dotfiles-v4l2loopback.conf` with `exclusive_caps=1`
(Chromium lists the device only with it) and loads the module now and at every boot. A
module already loaded with other options is not unloaded, since that would cut
a running camera; the run prints the reload command instead. OBS reopens the
last profile and collection; start the virtual camera from its Controls dock
before the meeting. Firefox asks PipeWire for cameras by default, and PipeWire
never adds a camera for this device: it checks the device at boot, before OBS
writes to it, when the device only accepts output. When Firefox is installed,
the role writes `/etc/firefox/policies/policies.json` so Firefox reads V4L2
cameras directly (`media.webrtc.camera.allow-pipewire` set to `false` as a
default value, still editable in `about:config`). Other policies in that file
are kept, and invalid JSON stops the run; `obs_virtualcam_firefox_v4l2: false`
skips it. In the browser, pick "OBS Virtual Camera" as the camera. The virtual
camera carries no sound, so pick the microphone in the meeting as usual.

### SAML VPN

The `23_vpn` group installs `openfortivpn`; only PadsP5560 selects it, in
`group_vars/host_PadsP5560.yml`. The `vpn` tag of the `system` role then configures the
`openfortivpn@work.service` instance. Its gateway comes from an Ansible Vault
file that Git ignores, so neither the repository nor its mirrors hold it:

```sh
mkdir -p ansible/group_vars/all
ansible-vault create --vault-password-file .vault ansible/group_vars/all/vault_vpn.yml
```

```yaml
vault_vpn_gateway_host: vpn.example.com
vault_vpn_gateway_port: 443
```

Without `vault_vpn_gateway_host`, or on a host without `23_vpn`, the tasks
change nothing and leave files of an earlier run in place. The host must be a
DNS name and the ports numbers: a newline or a space could otherwise add
settings to the daemon configuration or the polkit rule.

The role writes:

- `/etc/openfortivpn/work.conf` (root, `0600`): SAML login on local port 8020,
  `set-dns = 1` and `use-resolvconf = 1`. The DNS servers and search domains
  reach systemd-resolved on the `ppp0` link through `systemd-resolvconf`, so
  `/etc/resolv.conf` stays the stub link of the DNS policy and the link
  settings disappear with the tunnel, even after a crash.
- A unit drop-in with `TimeoutStartSec=5min` (the unit is ready only after
  the browser login) and `Restart=no` (each attempt needs a new login).
- `/etc/polkit-1/rules.d/60-dotfiles-vpn.rules`: the users in
  `system_vpn_users` (default: the user running Ansible), from an active local
  session, may start and stop that unit without a password. Other units and
  verbs keep the default policy.
- `/etc/openfortivpn/waybar.json`: the unit name and the login URL, read by
  the Waybar `VPN` module. A click starts the unit and opens the login page;
  the indicator turns yellow while it waits for the browser and green once the
  tunnel is up. A second click disconnects.

From a terminal, the same unit works without Waybar:

```sh
systemctl start --no-block openfortivpn@work.service
journalctl -fu openfortivpn@work.service
```
