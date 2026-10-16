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
local CPU builds on Arch Linux and CachyOS. Vim plugin updates are opt-in with
`-e dotfiles_update_vim_plugins=true`.

Run `./install --tags makepkg --ask-become-pass` to configure makepkg without
running the other setup tasks. The existing `makepkg_config` tag remains
available as an alias.

Package groups are split by OS family in `roles/packages/vars/`. The package
role loads the matching file and keeps selection, installation, and
reconciliation in separate task files.

On Arch Linux and CachyOS, the package role enables `Color`, `CheckSpace`, and
the standard `multilib` repository in `/etc/pacman.conf`, and sets
`ParallelDownloads = 5`. When it enables `multilib`, it runs `pacman -Syu`,
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
