# Manual Arch Linux installation (LUKS and LVM)

This is a worked example for installing Arch Linux on a UEFI system with an
LVM volume group inside a LUKS-encrypted root partition. The EFI System
Partition (`/efi`) stays unencrypted. `/boot` is a directory on the encrypted
root filesystem, not a separate partition. These commands erase or repartition
disks: adapt them to the target machine.

For current installation and security guidance, start with the
[Arch Linux Installation Guide](https://wiki.archlinux.org/title/Installation_guide)
and the [dm-crypt encryption guide](https://wiki.archlinux.org/title/Dm-crypt/Encrypting_an_entire_system).
An unencrypted EFI System Partition does not protect boot files from offline
modification. Read the
[Secure Boot guide](https://wiki.archlinux.org/title/Unified_Extensible_Firmware_Interface/Secure_Boot)
if that threat matters to you.

The workstations run CachyOS, which builds on Arch and adds CPU-optimized
repositories, its own kernels and `cachyos-settings`. You can install it with
the [CachyOS installer](https://wiki.cachyos.org/installation/installation_on_root/)
and go straight to the [quick start](../../QUICKSTART.md), or follow this
guide and then add the [CachyOS repositories](#cachyos-repositories). In both
cases, read the
[CachyOS post-install setup](https://wiki.cachyos.org/configuration/post_install_setup/).

This guide only covers what has to happen before Ansible can run. Once the
system boots, the [quick start](../../QUICKSTART.md) deploys the dotfiles, and
the roles under [`ansible/roles`](../../ansible/roles/) handle packages,
services, drivers and desktop settings.

## Preface

This page keeps a GRUB-based example.
[Huntrar's current guide](https://gist.github.com/huntrar/e42aee630bee3295b2c671d098c81268)
now uses systemd-boot and unified kernel images. Follow the ArchWiki for
bootloader-specific details.

The device examples use `/dev/nvme0n1`. Replace the disk and partition paths,
partition sizes and logical volume sizes to match your hardware.

Arch Linux changes often. Check package names and commands against the
official wiki before using this machine-specific example. You can also install
with `archinstall`, then continue with the [quick start](../../QUICKSTART.md).

## Table of contents

[[_TOC_]]

# Create a USB installer

Download the ISO and its detached signature from the official
[Arch Linux downloads page](https://archlinux.org/download/), and verify the
signature before writing the image. Replace the date below with the filename
you downloaded.

```sh
gpg --auto-key-locate clear,wkd --locate-external-key pierre@archlinux.org
gpg --fingerprint pierre@archlinux.org
gpg --verify archlinux-YYYY.MM.DD-x86_64.iso.sig archlinux-YYYY.MM.DD-x86_64.iso
```

Compare the displayed fingerprint with the one on the downloads page before
you trust the signature.

Identify the USB device with `lsblk` and check its model and size. Writing the
image erases the selected device. Use the whole device, not a partition. Find
its stable path with `ls -l /dev/disk/by-id/usb-*`, and replace the example
only after checking it:

```sh
lsblk -o NAME,PATH,SIZE,MODEL,TRAN
sudo dd bs=4M if=archlinux-YYYY.MM.DD-x86_64.iso of=/dev/disk/by-id/usb-REPLACE_ME conv=fsync status=progress
```

# Boot into the live environment

Check that the machine booted in UEFI mode, that the network works and that
the clock is synchronized:

```sh
cat /sys/firmware/efi/fw_platform_size   # 64 on a 64-bit UEFI; missing in BIOS mode
ping -c 3 archlinux.org
timedatectl
```

The example creates a 1 MiB BIOS boot partition, a 1 GiB EFI System Partition
and one LUKS partition on the remaining space. A UEFI-only system does not need
the BIOS boot partition. If you leave it out, update the partition numbers in
the commands below.

## Partitions

### Create

Check the target disk with `lsblk` before you start. The `o` command below
replaces its partition table.

```text
gdisk /dev/nvme0n1
o
n
[Enter]
0
+1M
ef02
n
[Enter]
[Enter]
+1G
ef00
n
[Enter]
[Enter]
[Enter]
8309
w
```

### LUKS

```sh
cryptsetup luksFormat --type luks2 /dev/nvme0n1p3
cryptsetup luksOpen /dev/nvme0n1p3 cryptlvm
```

GRUB unlocks the encrypted `/boot` itself, so it must support the LUKS2
key-derivation function of at least one key slot. `luksFormat` uses Argon2id
by default. The GRUB package in Arch `core` (2.16) reads Argon2i, Argon2id and
PBKDF2: its `luks2` module depends on an `argon2` module. Older GRUB builds
read PBKDF2 only. Before you reboot, check that the GRUB you installed ships
that module:

```sh
grep '^luks2:' /usr/lib/grub/x86_64-efi/moddep.lst   # must list argon2
```

If `argon2` is missing, add a PBKDF2 key slot with
`cryptsetup luksAddKey --pbkdf pbkdf2 /dev/nvme0n1p3`, otherwise the machine
will not boot.

A LUKS header backup can recover from header damage, but it also lets someone
try offline passphrase guesses. Protect it, store it away from the encrypted
disk, and do not count on it to recover a forgotten passphrase.

```sh
cryptsetup luksHeaderBackup /dev/nvme0n1p3 \
  --header-backup-file /path/on/offline-storage/cryptlvm-header.img
```

#### TRIM through LUKS

dm-crypt drops discard requests by default, so the weekly `fstrim.timer` that
Ansible enables does nothing on the encrypted volumes. To allow discards, store
the flag in the LUKS2 header once the system is installed, then reboot:

```sh
cryptsetup --allow-discards --persistent refresh cryptlvm
lsblk --discard   # DISC-GRAN and DISC-MAX must not be 0 for cryptlvm
```

Discards reveal which blocks are free, which leaks the rough amount of data and
the filesystem type. See the
[ArchWiki dm-crypt TRIM notes](<https://wiki.archlinux.org/title/Dm-crypt/Specialties#Discard/TRIM_support_for_solid_state_drives_(SSD)>).

### LVM

```sh
RAM_SIZE=$(($(getconf _PHYS_PAGES) * $(getconf PAGE_SIZE) / (1024 * 1024)))

pvcreate /dev/mapper/cryptlvm
vgcreate archlvm /dev/mapper/cryptlvm

lvcreate -L 32G archlvm -n slash
lvcreate -L 30G archlvm -n opt
lvcreate -L 10G archlvm -n var_lib_docker
lvcreate -L "${RAM_SIZE}M" archlvm -n swap
lvcreate -l 100%FREE archlvm -n home
```

The swap volume matches the RAM size so the machine can hibernate. Without
hibernation you can drop it: `cachyos-settings` sets up swap on zram, and
`zram-generator` does the same on plain Arch.

### Format

```sh
mkfs.fat -F32 /dev/nvme0n1p2                     -n EFI
mkfs.ext4     /dev/mapper/archlvm-slash          -L slash
mkfs.ext4     /dev/mapper/archlvm-home           -L home
mkfs.ext4     /dev/mapper/archlvm-opt            -L opt
mkfs.ext4     /dev/mapper/archlvm-var_lib_docker -L var_lib_docker
mkswap        /dev/mapper/archlvm-swap           -L swap
swapon        /dev/mapper/archlvm-swap
```

### Mount

```sh
mount /dev/mapper/archlvm-slash /mnt
mkdir /mnt/efi /mnt/home /mnt/var/lib/docker /mnt/opt -p
mount /dev/nvme0n1p2                     /mnt/efi
mount /dev/mapper/archlvm-home           /mnt/home
mount /dev/mapper/archlvm-var_lib_docker /mnt/var/lib/docker
mount /dev/mapper/archlvm-opt            /mnt/opt
```

## System

### Install base

```sh
# Available kernel options:
# KERNEL='linux'     # Vanilla Linux kernel and modules, with a few patches applied.
# KERNEL='linux-lts' # Long-term support (LTS) Linux kernel and modules.
# KERNEL='linux-zen' # Result of a collaborative effort of kernel hackers to provide the best Linux kernel possible for everyday systems.
# KERNEL='linux-hardened' # Security-focused kernel with additional hardening features

KERNEL='linux'

# Available microcode options:
# UCODE='intel-ucode' # for Intel processors.
# UCODE='amd-ucode'   # for AMD processors.

UCODE='intel-ucode' # for Intel processors, adjust as needed

pacstrap -K /mnt \
  base \
  base-devel \
  ansible \
  cryptsetup \
  ${KERNEL} \
  ${KERNEL}-headers \
  ${UCODE} \
  wireless-regdb \
  efibootmgr \
  git \
  grub \
  linux-firmware \
  lvm2 \
  fastfetch \
  network-manager-applet \
  networkmanager \
  openssh \
  os-prober \
  python \
  systemd-resolvconf \
  rsync \
  sudo \
  terminus-font \
  vim \
  wpa_supplicant \
  zsh
```

Add `sof-firmware` on laptops whose built-in audio needs Sound Open Firmware,
which covers most recent Intel laptops. `os-prober` is only needed when
another operating system shares the machine, and GRUB ignores it until you set
`GRUB_DISABLE_OS_PROBER=false` in `/etc/default/grub`.

### Configure resolv.conf

systemd-resolved is the only resolver. Point `/etc/resolv.conf` at its stub
from outside the chroot, because `arch-chroot` bind-mounts that file. The
[`dns` role](../../ansible/roles/dns/README.md) then configures resolved and
NetworkManager.

```sh
ln -sf ../run/systemd/resolve/stub-resolv.conf /mnt/etc/resolv.conf
```

The same role migrates hosts installed with the earlier openresolv
instructions; follow the [DNS migration note](./dns-migration.md).

### Wi-Fi and audio

Nothing is needed here. The
[`wireless_regdom` role](../../ansible/roles/wireless_regdom/README.md) sets
the Wi-Fi regulatory domain (`wireless_regdom_country: FR` in
`group_vars/all/main.yml`). On a portable machine, the
[`power_save` role](../../ansible/roles/power_save/README.md) writes the HDA
audio power-saving options, and leaves Intel Wi-Fi power saving off unless
`power_save_wifi: true` is set.

### Create fstab

```sh
genfstab -U /mnt >> /mnt/etc/fstab
```

Do not add a `/tmp` line: systemd's `tmp.mount` already mounts `/tmp` as a
tmpfs with `nosuid,nodev`.

# Configure the installed system

```sh
arch-chroot /mnt
```

Check the resulting layout with `lsblk`. Device names and sizes will vary; this
output matches the example commands above.

| NAME                         | MAJ:MIN | RM  | SIZE   | RO  | TYPE  | MOUNTPOINT      |
| ---------------------------- | ------- | --- | ------ | --- | ----- | --------------- |
| nvme0n1                      | 259:0   | 0   | 953.9G | 0   | disk  |                 |
| ├─nvme0n1p1                  | 259:1   | 0   | 1M     | 0   | part  |                 |
| ├─nvme0n1p2                  | 259:2   | 0   | 1G     | 0   | part  | /efi            |
| ├─nvme0n1p3                  | 259:3   | 0   | 953.3G | 0   | part  |                 |
| ..└─cryptlvm                 | 254:0   | 0   | 953.3G | 0   | crypt |                 |
| ....├─archlvm-swap           | 254:1   | 0   | 31.1G  | 0   | lvm   | [SWAP]          |
| ....├─archlvm-slash          | 254:2   | 0   | 32G    | 0   | lvm   | /               |
| ....└─archlvm-home           | 254:3   | 0   | 850G   | 0   | lvm   | /home           |
| ....└─archlvm-opt            | 254:4   | 0   | 30G    | 0   | lvm   | /opt            |
| ....└─archlvm-var_lib_docker | 254:5   | 0   | 10G    | 0   | lvm   | /var/lib/docker |

## Build flags

Leave `/etc/makepkg.conf` alone. The
[`package_manager` role](../../ansible/roles/package_manager/README.md)
(`makepkg` tag) writes its native-CPU build flags to
`/etc/makepkg.conf.d/zz-dotfiles.conf`. A package built this way may not run on
a different CPU, so do not copy it to another computer.

## Time zone

```sh
# Replace Region/City with your time zone.
ln -sf /usr/share/zoneinfo/Region/City /etc/localtime
hwclock --systohc
```

## Locales

```sh
sed -i 's/^#\(fr_FR.UTF-8 UTF-8\)/\1/' /etc/locale.gen
sed -i 's/^#\(en_US.UTF-8 UTF-8\)/\1/' /etc/locale.gen
locale-gen
echo 'LANG=en_US.UTF-8'  > /etc/locale.conf
```

## Keymap

```sh
echo 'KEYMAP=us-acentos' > /etc/vconsole.conf
echo 'FONT=ter-116n'    >> /etc/vconsole.conf
```

The `sd-vconsole` initramfs hook reads this file, so the LUKS passphrase
prompt uses this keymap. Hyprland sets its own keyboard layout in the
dotfiles, and Xwayland applications use it, so no Xorg keyboard file is
needed.

## Hostname

```sh
myhostname='MyArch'
echo "${myhostname}" > /etc/hostname
```

Leave `/etc/hosts` as installed: systemd's `nss-myhostname` resolves the host
name and `localhost`. Ansible later reaches the machine by this name, so use
the one you will declare in `ansible/inventory.yml`.

## Boot

### GRUB

```sh
UUID=$(blkid /dev/nvme0n1p3 -s UUID -o value)

sed -i "/^GRUB_CMDLINE_LINUX=/cGRUB_CMDLINE_LINUX=\"rd.luks.name=${UUID}=cryptlvm root=/dev/mapper/archlvm-slash\"" /etc/default/grub

sed -i "/GRUB_ENABLE_CRYPTODISK=/cGRUB_ENABLE_CRYPTODISK=y" /etc/default/grub

grub-install --target=x86_64-efi --efi-directory=/efi --bootloader-id=ArchLinux
grub-mkconfig -o /boot/grub/grub.cfg
```

### initramfs

GRUB asks for the passphrase to read `/boot`. A key file embedded in the
initramfs then unlocks the root volume, so you type the passphrase only once.

```sh
mkdir -p /etc/cryptsetup-keys.d
head -c 64 /dev/urandom > /etc/cryptsetup-keys.d/cryptlvm.key
chmod 600 /etc/cryptsetup-keys.d/cryptlvm.key
cryptsetup -v luksAddKey /dev/nvme0n1p3 /etc/cryptsetup-keys.d/cryptlvm.key

# The key is embedded in the initramfs. Protect the boot chain and keep a
# separate recovery method; the EFI System Partition remains unencrypted.
sed -i '/^FILES/c\FILES=(/etc/cryptsetup-keys.d/cryptlvm.key)' /etc/mkinitcpio.conf
sed -i '/^HOOKS/c\HOOKS=(base systemd autodetect microcode modconf kms keyboard sd-vconsole block sd-encrypt lvm2 filesystems fsck)' /etc/mkinitcpio.conf
mkinitcpio -P
```

The `sd-encrypt` hook uses `/etc/cryptsetup-keys.d/cryptlvm.key` for the
`cryptlvm` mapping. See the ArchWiki's
[mkinitcpio encryption instructions](https://wiki.archlinux.org/title/Dm-crypt/System_configuration#mkinitcpio).

## Services

```sh
systemctl enable NetworkManager
systemctl enable systemd-resolved
```

The
[`time_sync` role](../../ansible/roles/time_sync/README.md) enables
`systemd-timesyncd` later, unless another NTP client such as chrony is in use.

## User

```sh
MYUSER='MyUser'
useradd -m -s /bin/zsh -G wheel "${MYUSER}"
EDITOR=vi visudo -f /etc/sudoers.d/wheel
passwd "${MYUSER}"
```

In `visudo`, add `%wheel ALL=(ALL:ALL) ALL` to require the user's password for
administrative commands. Do not edit sudoers files with a plain text editor.

Once `sudo` works for this user, you can lock the root account with
`passwd -l root`. systemd's emergency and rescue shells then refuse to open,
so a boot failure needs the live USB to repair. Otherwise, set a root password
with `passwd`.

### Package manager

Leave `/etc/pacman.conf` alone. The
[`package_manager` role](../../ansible/roles/package_manager/README.md) sets
its options and enables `multilib`, which runs a full `pacman -Syu`.

### CachyOS repositories

Skip this on a system installed with the CachyOS installer. On Arch, the
CachyOS script detects the CPU level, backs up `/etc/pacman.conf` and adds the
matching repositories above the Arch ones:

```sh
curl -O https://mirror.cachyos.org/cachyos-repo.tar.xz
tar xvf cachyos-repo.tar.xz && cd cachyos-repo
sudo ./cachyos-repo.sh
```

The archive is not signed, so read `cachyos-repo.sh` before you run it as
root. `sudo ./cachyos-repo.sh --remove` undoes it. Check the CPU level with
`/lib/ld-linux-x86-64.so.2 --help | grep supported`. Intel 12th generation and
later CPUs may list x86-64-v4, but AVX-512 is disabled on them, so use v3. The
`[cachyos]` repository replaces pacman with the CachyOS build. See
[CachyOS optimized repositories](https://wiki.cachyos.org/features/optimized_repos/).

CachyOS ranks its mirrors with `cachyos-rate-mirrors.timer`. Do not also
enable `reflector.timer`, because both rewrite the mirror lists.

### Dotfiles

You can clone the repository now, as the regular user:

```sh
# Run setup commands in the regular user's context.
sudo -u "${MYUSER}" -i bash -c '
  git clone https://gitlab.com/pad92/dotfiles.git ~/.dotfiles
  mkdir -p ~/.config
'
```

### Window manager and applications

Do not deploy from the chroot. The playbook connects over SSH to the host
named in the inventory and checks that its hostname matches, and its roles
start services through systemd. None of that works until the installed system
runs. Leave the chroot and reboot:

```sh
exit
```

```sh
sync
umount -R /mnt
reboot
```

After the first login, follow the [quick start](../../QUICKSTART.md). It
enables `sshd`, which Ansible needs even on the machine it runs from, then
adds the inventory entry and runs `make check` and `make deploy`. No role
configures `sshd`, so review `/etc/ssh/sshd_config` if the machine is
reachable from an untrusted network. Select only the package
groups the host needs; the lists include optional and hardware-specific groups
that should not all be installed together.

AUR packages are built with `yay`, which the
[`packages` role](../../ansible/roles/packages/README.md) builds first when it
is missing. `-e packages_aur_action=ask` confirms each AUR build, and
`-e packages_aur_action=skip` skips them. AUR build files are user-submitted:
review them before you install them, as the
[ArchWiki AUR guidance](https://wiki.archlinux.org/title/Arch_User_Repository)
explains.

# Optional

## Auto CPUfreq

No package group installs auto-cpufreq, and the roles assume
`power-profiles-daemon` instead. With the `21_steam` group, the
[`gaming` role](../../ansible/roles/gaming/README.md) offers to remove
auto-cpufreq (`gaming_power_manager_conflict_action`), and the
[`cpu_power` role](../../ansible/roles/cpu_power/README.md) leaves the AMD
energy preference alone while it runs. If you install it anyway:

```sh
sudo systemctl enable --now auto-cpufreq
```

## Firewall

The CachyOS installer enables `ufw`, which denies incoming and allows outgoing
connections. A system installed from this guide has no firewall, and no role
configures one. See the
[ArchWiki security guide](https://wiki.archlinux.org/title/Security#Firewalls)
and the [CachyOS post-install setup](https://wiki.cachyos.org/configuration/post_install_setup/).

## SSD Trim

The [`package_services` role](../../ansible/roles/package_services/README.md)
enables `fstrim.timer` with the `01_base` group. On the encrypted volumes it
needs [TRIM through LUKS](#trim-through-luks).

## Package cache

The [`package_services` role](../../ansible/roles/package_services/README.md)
also enables `paccache.timer` with the `01_base` group. It keeps the last three
versions of each package in the pacman cache.

## USBGuard

No role installs or configures USBGuard. Generate the policy with every device
you need plugged in, keyboard included: the daemon blocks any device the
policy does not list. The daemon refuses a rules file that other users can
read, hence the `0600` mode.

```sh
sudo pacman -S usbguard
sudo sh -c 'usbguard generate-policy > /etc/usbguard/rules.conf'
sudo chmod 0600 /etc/usbguard/rules.conf
sudo systemctl enable --now usbguard.service
```

The `usbguard-applet-qt` tray applet comes from the AUR; review it before you
build it.

## Docker

Select the `12_containers_docker` package group. The
[`docker` role](../../ansible/roles/docker/README.md) adds the user to the
`docker` group, which grants root-equivalent access to the Docker daemon. The
[`dns` role](../../ansible/roles/dns/README.md) sets the bridge address and the
DNS server in `daemon.json`.

## Nvidia

Select the NVIDIA driver group that matches the GPU; the
[`packages` role README](../../ansible/roles/packages/README.md) lists them.
Legacy and modern hardware have separate groups, so do not mix them. The
[`gpu` role](../../ansible/roles/gpu/README.md) manages the module options and
regenerates the initramfs when they change.

## Nvidia Prime

The NVIDIA package groups include `nvidia-prime`. Select the driver group that
matches the GPU instead of installing a second driver set by hand.

## GNOME Keyring PAM setup

The [`gnome_keyring` role](../../ansible/roles/gnome_keyring/README.md) adds
the `pam_gnome_keyring.so` rules to `/etc/pam.d/login`, for TTY logins.
Automatic unlock requires the login password and the keyring password to
match. Display managers may already configure PAM: set
`gnome_keyring_pam_enabled: false` and use their PAM file instead. See the
[ArchWiki GNOME Keyring guide](https://wiki.archlinux.org/title/GNOME/Keyring)
for other login methods.

## Start Hyprland with UWSM

[UWSM](https://github.com/Vladimir-csp/uwsm) (Universal Wayland Session
Manager) runs the compositor in systemd units and manages the session
environment and applications. The
[Hyprland wiki](https://wiki.hypr.land/Useful-Utilities/Systemd-start/) has
the full documentation.

### Installation

The `01_base` package group installs `uwsm` and `libnewt`, which provides the
`whiptail` menu that `uwsm select` shows.

### Launch from TTY

The [`dotfiles` role](../../ansible/roles/dotfiles/README.md) installs
`~/.zprofile`, which runs this only for a login shell attached to a terminal.

#### Option A: Interactive selection menu at login

This is the installed version:

```zsh
if [[ -o login && -t 0 ]] && command -v uwsm >/dev/null 2>&1; then
    if uwsm check may-start && uwsm select; then
        exec uwsm start default
    fi
fi
```

#### Option B: Direct launch

To skip the menu, replace it with:

```zsh
if [[ -o login && -t 0 ]] && command -v uwsm >/dev/null 2>&1; then
    if uwsm check may-start; then
        exec uwsm start hyprland.desktop
    fi
fi
```

A later deploy restores the installed version. With a display manager, select
`Hyprland (uwsm-managed)` instead.

### Application launching

Launch graphical applications as systemd scopes:

```sh
uwsm app -- alacritty
```

### Autostart

The systemd session target starts XDG autostart entries. Enable native user
services in the usual way:

```sh
systemctl --user enable <service>
# If the service lacks an [Install] section:
systemctl --user add-wants graphical-session.target <service>
```

## Real-time audio scheduling

PipeWire gets real-time scheduling from `rtkit`, part of the `01_base` group.
Do not install `realtime-privileges`: its limits let Chromium and Electron apps
run at nice -8, along with every process they start, and that load then
starves a WebRTC call in Firefox.

On a machine that already has it, the
[`package_services` role](../../ansible/roles/package_services/README.md)
removes the user from the `realtime` group and writes a `nice 0` limit for the
user, which also overrides the `audio` group limit from `cachyos-settings`.
Close every session of the user, or reboot: the systemd user manager keeps the
limits it started with.

The deploy does not remove the package. Reconcile with
`make deploy ANSIBLE_ARGS="-e packages_action=reconcile"` and type `REMOVE`.
The reconcile only removes packages this repository installed, so otherwise
run `sudo pacman -Rs realtime-privileges`.

To check that PipeWire has a real-time thread (`FF` class):

```sh
ps -L -o cls=,rtprio=,comm= -p "$(pgrep -u "$USER" -x pipewire)"
```

After a new login, `ulimit -e` prints `20` (lowest nice 0), not `31` (-11).

## Security follow-up

Security settings depend on how the machine is used and who can access it.
The [ArchWiki security recommendations](https://wiki.archlinux.org/title/Security)
cover networking, remote access, updates, Secure Boot and backups. Keep an
independently stored backup of the LUKS header and recovery material, and do
not store the only copy on the encrypted disk.
