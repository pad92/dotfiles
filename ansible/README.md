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

Package groups are split by OS family in `roles/packages/vars/`. The package
role loads the matching file and keeps selection, installation, and
reconciliation in separate task files.

Package groups are selected automatically from OS defaults and detected GPU
facts. Configure exact selections by hostname in `host_vars/localhost.yml`; those
lists replace the defaults. `packages_group_selection` remains available as a
one-run override. When using Vault-encrypted content, pass
`--vault-password-file .vault` to `./install`; the local password file is
ignored by Git. Example of a one-run package group override:

```sh
./install --ask-become-pass \
  -e '{"packages_group_selection":["01_base","03_gtk"]}'
```

Conflicting regular files and directories that need a type change are moved to
a `.bak` path. Existing symbolic links at managed paths are removed without a
backup; their targets are left untouched. Package installation is additive.
On Arch Linux, installing selected packages does not upgrade the whole system
by default. Set `-e packages_upgrade_system=true` to use `pacman -Syu` when
installing missing packages. Use `--check` to preview package changes and
`-e packages_action=reconcile` to enable explicit, ownership-based removals.
Use `--check --tags dotfiles` to preview dotfile link changes separately.
