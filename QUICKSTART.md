# Quick start

This guide takes a new user from a fresh machine to a working Hyprland
desktop configured by this repository. It assumes you know a shell, but not
Ansible. Each step links to the reference page that covers it in depth.

The repository holds its author's own settings: two hosts, two external
monitors, French wireless rules. Fork it, or work on a branch of your clone,
so your commits stay separate from upstream.

## 1. Check what you need

Ansible runs from a controller and configures a target over SSH. On a single
machine, the controller and the target are the same computer, and Ansible
still connects to it over SSH.

On the target:

- Arch Linux or CachyOS. For a fresh Arch system, follow the
  [Arch installation guide](./dist/arch/install.md) first. The playbook
  also accepts Debian, Ubuntu and Fedora, with fewer package groups: Debian
  and Ubuntu define no Hyprland group, and several roles act on Arch only.
- A regular user with `sudo` access.
- An SSH server that accepts your key. No role configures `sshd`.
- Network access to GitHub, to clone the pinned Zsh and Vim plugins.

On the controller:

- Git and `make`.
- `ansible-core` 2.21 or later, or the full `ansible` package.

On Arch, this installs everything and lets your own user log in over SSH:

```sh
sudo pacman -S --needed git make ansible openssh
sudo systemctl enable --now sshd
ssh-keygen -t ed25519            # skip if ~/.ssh/id_ed25519 exists
ssh-copy-id "$(uname -n | cut -d. -f1)"
ssh "$(uname -n | cut -d. -f1)" true && echo "SSH OK"
```

The last command must print `SSH OK` without asking for a password. If the
hostname does not resolve, see [Troubleshooting](#troubleshooting).

## 2. Clone the repository

Clone your fork, or the upstream repository:

```sh
git clone https://gitlab.com/pad92/dotfiles.git ~/.dotfiles
cd ~/.dotfiles
```

The clone only has to exist on the controller. Once the target is deployed,
the configuration lives in your home directory.

## 3. Declare your machine

Ansible only configures hosts listed in `ansible/inventory.yml`, by short
hostname. Find yours:

```sh
uname -n | cut -d. -f1
```

Add it under `hosts` in [`ansible/inventory.yml`](./ansible/inventory.yml),
then create its host file, even an empty one:

```yaml
# ansible/inventory.yml
all:
  hosts:
    my-laptop:
```

```sh
touch ansible/host_vars/my-laptop.yml
```

The playbook stops if the machine it reaches reports a hostname other than
its inventory name; see
[Hostname check](./ansible/README.md#hostname-check).

The host file sets what differs on this machine. An empty file installs the
default package groups for your distribution (on Arch: `01_base`, `03_gtk`,
`11_hyprland`, and the groups of the GPUs found, see
[Graphics cards](#graphics-cards)). To get the full workstation set
instead, add the line below. It only works on Arch: the other distributions
lack some of its groups, and the playbook stops on an unsupported group.

```yaml
# ansible/host_vars/my-laptop.yml
packages_host_groups: '{{ packages_workstation_groups }}'
```

[`group_vars/all/packages.yml`](./ansible/group_vars/all/packages.yml) lists
the groups and what each one installs. See
[Per-host settings](./ansible/README.md#per-host-settings) for the other
options.

## 4. Adapt the shared settings

[`ansible/group_vars/all/main.yml`](./ansible/group_vars/all/main.yml) holds
the author's desktop settings, which apply to every host:

- `dotfiles_hypr_shared_monitors` names two specific monitors, a Dell
  P2423DE and an ASUS XG32WCS, and places one to the right of the other.
- `dotfiles_hypr_shared_workspace_rules` pins workspaces 1 and 2 to them.
- `wireless_regdom_country: FR` sets the Wi-Fi regulatory domain.

Monitors that no entry matches still work: each one joins the right edge of
the rightmost monitor. Set `wireless_regdom_country` to your country code. To
change one machine only, override a variable in its host file instead of
editing `main.yml`.

### Describe your own monitors

Each monitor is identified by the start of its `description:` line. From a
running Hyprland session, list them:

```sh
hyprctl monitors all | grep description:
```

Then describe them in your host file. Give each monitor a name of your
choice, and place it relative to another one with `right_of`, `left_of`,
`above` or `below`:

```yaml
# ansible/host_vars/my-laptop.yml
dotfiles_hypr_monitors:
  - name: laptop
    internal: true # the built-in panel
  - name: desk
    match: Vendor Name MODEL123 # start of the description, no serial
    above: laptop

dotfiles_hypr_workspace_rules:
  - workspace: 1
    monitor: desk
    default: true
```

Override `dotfiles_hypr_workspace_rules` too, or set it to `[]`. The shared
rules point to the `asus` and `dell` monitors, and the playbook stops when a
rule names a monitor that `dotfiles_hypr_monitors` does not define. The
[`dotfiles` role guide](./ansible/roles/dotfiles/README.md) lists the other
options: refresh mode, 10-bit color, identical monitors.

### Graphics cards

On Arch Linux and CachyOS there is nothing to declare. The playbook reads the
PCI devices of the target, then adds the package groups that match its AMD,
Intel or NVIDIA GPUs. The `gpu` role also detects a hybrid laptop by itself.
`make plan` shows the groups it picked. The other distributions define no GPU
group, so install their drivers yourself.

## 5. Install the Ansible collections

The full `ansible` package ships the collections the playbook needs. With
`ansible-core` alone, install the versions pinned in
[`ansible/requirements.yml`](./ansible/requirements.yml) into the repository:

```sh
make galaxy
```

They land in `.ansible/collections`, which `ansible.cfg` already points to.

## 6. Preview, then deploy

Run each step in order and read its output before the next one.

```sh
make plan BECOME_PASS=1       # package plan only, changes nothing
make check BECOME_PASS=1      # dry run with diffs
make deploy BECOME_PASS=1     # apply
```

The playbook uses `sudo` even for a preview, so `BECOME_PASS=1` asks for your
password once, at the start. Leave it out if your `sudo` needs none.

`make plan` lists the packages each group would install or skip. `make check`
runs every role in check mode and shows the file diffs. `make deploy`
installs the packages, changes the system settings and deploys the dotfiles to
your home directory, after backing up any file it replaces.

Installation is additive: packages that were already installed stay
unmanaged, and the playbook never removes them.

## 7. Set your Git identity

The managed `~/.gitconfig` includes `~/.gitconfig.local`, which Git does not
track. Put your identity there:

```sh
git config --file ~/.gitconfig.local user.name "Your Name"
git config --file ~/.gitconfig.local user.email "you@example.com"
```

## 8. Optional: the Vault

The Vault holds the encrypted values in `group_vars/all/vault.yml`. Only the
`vpn` role needs it, and only for the author's VPN gateway. A clone without a
`.vault` password file at the repository root runs without it. See
[Vault](./ansible/README.md#vault) if you want to keep your own secrets there.

## 9. Start the desktop

Log out, then start Hyprland from a TTY or your display manager. The
[session guide](./dist/arch/install.md#gnome-keyring-pam-setup) covers TTY
startup, GNOME Keyring, UWSM, and the systemd session.

A few shortcuts to start with:

| Shortcut         | Action                                   |
| :--------------- | :--------------------------------------- |
| `SUPER + Return` | Terminal                                 |
| `SUPER + D`      | Application menu                         |
| `SUPER + F1`     | List the keybindings Hyprland has loaded |
| `SUPER + L`      | Lock                                     |
| `SUPER + Delete` | Logout menu                              |

The [Desktop](./README.md#desktop) section lists all of them.

## 10. Day-to-day use

Run `make help` for every target. The commands you will use most:

| Goal                              | Command                                         |
| :-------------------------------- | :---------------------------------------------- |
| Redeploy the dotfiles only        | `make deploy TAGS=dotfiles_deploy`              |
| Preview the dotfiles only         | `make check TAGS=dotfiles`                      |
| List the tags you can select      | `make tags`                                     |
| Configure another inventory host  | `make deploy HOST=other-host BECOME_PASS=1`     |
| Pull upstream changes and reapply | `git pull`, then `make check` and `make deploy` |
| Remove backups and leftovers      | `make clean DRY_RUN=1`, then `make clean`       |

To change a configuration file, edit it under
`ansible/roles/dotfiles/files/` or `ansible/roles/dotfiles/templates/` and
redeploy. A file edited directly in your home directory is overwritten on the
next deploy. [Customize](./README.md#customize) maps each program to its
source.

## Troubleshooting

### No hosts to target

Ansible prints `Specified inventory, host pattern and/or --limit leaves us
with no hosts to target`. Your hostname is missing from
`ansible/inventory.yml`, or differs from it in case. Copy the output of
`uname -n | cut -d. -f1` exactly.

### The play stops on "reached a machine named ..."

The machine Ansible reached reports a hostname that differs from its
inventory name. Check which machine SSH connects to, and that the inventory
name matches `uname -n` on it.
[Hostname check](./ansible/README.md#hostname-check) explains the fix.

### UNREACHABLE or Permission denied (publickey)

Run `ssh <hostname> true` by hand. If the name does not resolve, add
`ansible_host: localhost` (or the machine's address) to its host file. If the
key is refused, run `ssh-copy-id` again and check that `sshd` is running.

### Missing sudo password

Add `BECOME_PASS=1` to the command.

### couldn't resolve module/action

The `community.general` or `ansible.posix` collection is missing or too old.
Run `make galaxy`, or `make galaxy-force` to reinstall them.

## Further reading

- [README](./README.md): features, editor packages, tags, gaming.
- [Ansible guide](./ansible/README.md): layout, variables, Vault, cleanup,
  and the role list.
- [Arch installation guide](./dist/arch/install.md): installing Arch before
  the first deploy.
- [Changelog](./CHANGELOG.md): what changed in each release.
