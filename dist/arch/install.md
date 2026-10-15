# Arch Linux Manual Installation Guide (LUKS and LVM)

This is a worked example for installing Arch Linux on a UEFI system with an
LVM volume group inside a LUKS-encrypted root partition. The EFI System
Partition (`/efi`) remains unencrypted; `/boot` is a directory on the encrypted
root filesystem, not a separate encrypted partition. These commands erase or
repartition disks and need to be adapted to the target machine.

For current installation and security guidance, start with the
[Arch Linux Installation Guide](https://wiki.archlinux.org/title/Installation_guide)
and the [dm-crypt encryption guide](https://wiki.archlinux.org/title/Dm-crypt/Encrypting_an_entire_system).
An unencrypted EFI System Partition does not protect boot files from offline
modification. Consult the
[Secure Boot guide](https://wiki.archlinux.org/title/Unified_Extensible_Firmware_Interface/Secure_Boot)
if that threat matters.

## Preface

This page retains a GRUB-based example. [Huntrar's current guide](https://gist.github.com/huntrar/e42aee630bee3295b2c671d098c81268)
now uses systemd-boot and unified kernel images; follow the ArchWiki for
bootloader-specific details.

_Note:_ The device examples use `/dev/nvme0n1`. Replace the disk and partition
paths, partition sizes, and logical volume sizes to match your hardware.

Arch Linux changes frequently. Check package names and commands against the
official wiki before using this machine-specific example. You can also use
`archinstall` and follow the dotfiles setup section below.

## Table of contents

[[_TOC_]]

# Create a USB installer

Download the ISO and its detached signature from the official
[Arch Linux downloads page](https://archlinux.org/download/). Verify the
signature before writing the image. Replace the date below with the filename
you downloaded.

```sh
gpg --auto-key-locate clear,wkd --locate-external-key pierre@archlinux.org
gpg --fingerprint pierre@archlinux.org
gpg --verify archlinux-YYYY.MM.DD-x86_64.iso.sig archlinux-YYYY.MM.DD-x86_64.iso
```

Compare the displayed fingerprint with the one on the downloads page before
accepting the signature.

Identify the USB device with `lsblk` and verify its model and size. Writing the
image erases the selected device. Use the whole device, not a partition. Find
its stable path with `ls -l /dev/disk/by-id/usb-*` and replace the example only
after checking it:

```sh
lsblk -o NAME,PATH,SIZE,MODEL,TRAN
sudo dd bs=4M if=archlinux-YYYY.MM.DD-x86_64.iso of=/dev/disk/by-id/usb-REPLACE_ME conv=fsync status=progress
```

# Boot into the live environment

The example creates a 1 MiB BIOS boot partition, a 550 MiB EFI System
Partition, and one LUKS partition using the remaining space. The BIOS boot
partition is not needed for UEFI-only systems; omit it only if you also update
the partition numbers used below.

## Partitions

### Create

Check the target disk with `lsblk` before starting. The `o` command below
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
+550M
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

Before relying on GRUB to unlock the encrypted `/boot`, check that the installed
GRUB version supports the LUKS2 key-derivation function in use. See the
[ArchWiki GRUB guidance](https://wiki.archlinux.org/title/GRUB#LUKS2).
Keep the default key-derivation settings unless the bootloader requires a
compatible alternative. A LUKS header backup can recover from header damage, but
it also lets someone attempt offline passphrase guesses. Protect it, store it
separately from the encrypted disk, and do not rely on it to recover a forgotten
passphrase.

```sh
cryptsetup luksHeaderBackup /dev/nvme0n1p3 \
  --header-backup-file /path/on/offline-storage/cryptlvm-header.img
```

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
  irqbalance \
  linux-firmware \
  lvm2 \
  fastfetch \
  network-manager-applet \
  networkmanager \
  openssh \
  os-prober \
  python \
  openresolv \
  rsync \
  sudo \
  terminus-font \
  vim \
  wpa_supplicant \
  zsh
```

### Configure resolv.conf

```sh
echo '[main]
rc-manager=resolvconf' > /mnt/etc/NetworkManager/conf.d/rc-manager.conf
```

### Configure wifi

```sh
echo 'WIRELESS_REGDOM="FR"' > /mnt/etc/conf.d/wireless-regdom
echo "options iwlwifi power_save=1"     > /mnt/etc/modprobe.d/iwlwifi.conf
echo "options iwlwifi uapsd_disable=0" >> /mnt/etc/modprobe.d/iwlwifi.conf
if grep -wq '^iwlmvm' /proc/modules; then
  echo "options iwlmvm power_scheme=3" >> /mnt/etc/modprobe.d/iwlwifi.conf
elif grep -wq '^iwldvm' /proc/modules; then
  echo "options iwldvm force_cam=0"    >> /mnt/etc/modprobe.d/iwlwifi.conf
fi
```

### Sound

```sh
if grep -wq '^snd_hda_intel' /proc/modules; then
echo "options snd_hda_intel power_save=1" > /mnt/etc/modprobe.d/audio_powersave.conf
elif grep -wq '^snd_ac97_codec' /proc/modules; then
echo "options snd_ac97_codec power_save=1" > /mnt/etc/modprobe.d/audio_powersave.conf
fi
```

### Create fstab

```sh
genfstab -U /mnt                                           >> /mnt/etc/fstab
echo 'tmpfs     /tmp tmpfs defaults,noatime,mode=1777 0 0' >> /mnt/etc/fstab
```

# Configure the installed system

```sh
arch-chroot /mnt
```

Check the resulting layout with `lsblk`. Device names and sizes will vary; this
output illustrates the example commands above.

| NAME                         | MAJ:MIN | RM  | SIZE   | RO  | TYPE  | MOUNTPOINT      |
| ---------------------------- | ------- | --- | ------ | --- | ----- | --------------- |
| nvme0n1                      | 259:0   | 0   | 953.9G | 0   | disk  |                 |
| ├─nvme0n1p1                  | 259:1   | 0   | 1M     | 0   | part  |                 |
| ├─nvme0n1p2                  | 259:2   | 0   | 550M   | 0   | part  | /efi            |
| ├─nvme0n1p3                  | 259:3   | 0   | 953.3G | 0   | part  |                 |
| ..└─cryptlvm                 | 254:0   | 0   | 953.3G | 0   | crypt |                 |
| ....├─archlvm-swap           | 254:1   | 0   | 31.1G  | 0   | lvm   | [SWAP]          |
| ....├─archlvm-slash          | 254:2   | 0   | 32G    | 0   | lvm   | /               |
| ....└─archlvm-home           | 254:3   | 0   | 850G   | 0   | lvm   | /home           |
| ....└─archlvm-opt            | 254:4   | 0   | 30G    | 0   | lvm   | /opt            |
| ....└─archlvm-var_lib_docker | 254:5   | 0   | 10G    | 0   | lvm   | /var/lib/docker |

## Build flags

Keep the default `/etc/makepkg.conf` unless you have a specific reason to change
it. `-march=native` produces packages optimized for the build machine and can
make them unsuitable for other computers. Custom compression settings can also
increase build time without improving runtime performance.

## Time zone

```sh
# Replace Region/City with your time zone.
ln -sf /usr/share/zoneinfo/Region/City /etc/localtime
hwclock --systohc
```

## Locales

```sh
sed -i 's/^#fr_FR/fr_FR/g' /etc/locale.gen
sed -i 's/^#en_US/en_US/g' /etc/locale.gen
locale-gen
echo 'LANG=en_US.UTF-8'  > /etc/locale.conf
```

## Keymap

```sh
echo 'KEYMAP=us-acentos' > /etc/vconsole.conf
echo 'FONT=ter-116n'    >> /etc/vconsole.conf

mkdir -p /etc/X11/xorg.conf.d
cat <<EOF>/etc/X11/xorg.conf.d/00-keyboard.conf
# Set the Xorg keyboard layout. Adjust this for your keyboard.
Section "InputClass"
        Identifier "system-keyboard"
        MatchIsKeyboard "on"
        Option "XkbLayout" "us"
        Option "XkbVariant" "intl"
EndSection
EOF
```

## Hostname

```sh
myhostname='MyArch'
echo "${myhostname}" > /etc/hostname
cat <<EOF>> /etc/hosts
127.0.0.1  localhost
127.0.1.1  ${myhostname} ${myhostname}.localdomain
::1        localhost ip6-localhost ip6-loopback
ff02::1    ip6-allnodes
ff02::2    ip6-allrouters
EOF
```

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
systemctl enable systemd-timesyncd.service
```

## User

```sh
MYUSER='MyUser'
useradd -m -s /bin/zsh -G wheel "${MYUSER}"
EDITOR=vi visudo -f /etc/sudoers.d/wheel
passwd "${MYUSER}"
```

In `visudo`, add `%wheel ALL=(ALL:ALL) ALL` to require the user's password for
administrative commands. Do not edit sudoers files with a plain text editor.

### Package manager

```sh
# Enable color, disk-space checks, and the official multilib repository.
sed -i 's/#Color/Color/' /etc/pacman.conf
sed -i 's/#CheckSpace/CheckSpace/' /etc/pacman.conf
sed -i '/^#\[multilib\]/,/^#Include = \/etc\/pacman.d\/mirrorlist/ s/^#//' /etc/pacman.conf
pacman -Syu
```

The Ansible installer enables `Color`, `CheckSpace`, and `multilib` in
`/etc/pacman.conf`, and sets `ParallelDownloads = 5`. When it enables
`multilib`, it runs `pacman -Syu`, which syncs package databases and upgrades
installed packages. Run `pacman -Syu` separately when you want a full system
upgrade and `multilib` is already enabled. The base and Steam groups include
`lib32-*` packages from `multilib`.

### Dotfiles

```sh
# Run setup commands in the regular user's context.
sudo -u "${MYUSER}" -i bash -c '
  git clone https://gitlab.com/pad92/dotfiles.git ~/.dotfiles
  mkdir -p ~/.config
'
```

### AUR packages

The dotfiles installer uses `paru` or `yay` when available. If neither is
installed, it can offer to build `yay-bin`; declining skips AUR packages.
Review AUR build files before installing them. See the
[ArchWiki AUR guidance](https://wiki.archlinux.org/title/Arch_User_Repository)
for the security model and recommended workflow.

### Window manager and applications

Install the dotfiles and selected package groups as the regular user. The
read-only package plan is optional. Avoid passing every package list to an AUR
helper: the lists contain optional and hardware-specific groups that should not
all be installed together.

```sh
sudo -u "${MYUSER}" -i bash -c '~/.dotfiles/install --check'
sudo -u "${MYUSER}" -i bash -c '~/.dotfiles/install'
```

```sh
exit
```

```sh
sync
umount -R /mnt
reboot
```

# Optional

## Auto CPUfreq

```sh
sudo systemctl enable --now auto-cpufreq
```

## SSD Trim

```sh
sudo systemctl enable fstrim.timer
```

## USBGuard

```sh
yay -S usbguard usbguard-applet-qt
sudo usbguard generate-policy | sudo tee /etc/usbguard/rules.conf
sudo systemctl start usbguard.service
sudo systemctl enable usbguard.service
```

## Docker

Select the Docker package group in the dotfiles installer. For access to the
Docker daemon without `sudo`, follow the Docker post-install guidance and
consider the security implications of membership in the `docker` group.

## Nvidia

Select the matching NVIDIA driver group in the dotfiles installer. It separates
legacy and modern hardware; avoid mixing both groups. Rebuild the initramfs only
if your chosen driver setup requires it.

## Nvidia Prime

The NVIDIA package groups include `nvidia-prime`. Select the driver group that
matches the GPU rather than installing a second driver set manually.

## Spotify

For Spotify client versions that store preferences in
`~/.config/spotify/Users/<user>-user/prefs`, add this setting to disable desktop
notifications. Preserve the file's other settings.

```ini
ui.track_notifications_enabled=false
```

## GNOME Keyring PAM Setup

For TTY logins, append these entries to the matching sections in
`/etc/pam.d/login`. Keep the existing PAM rules. Automatic unlock requires the
login password and the keyring password to match. Display managers may already
configure PAM; use their PAM file instead of `/etc/pam.d/login` when applicable.

```ini
auth       optional     pam_gnome_keyring.so
session    optional     pam_gnome_keyring.so    auto_start
```

See the [ArchWiki GNOME Keyring guide](https://wiki.archlinux.org/title/GNOME/Keyring)
for other login methods and password-change integration.

## Start Hyprland with UWSM

For complete documentation, see [Hyprland Wiki](https://wiki.hypr.land/Useful-Utilities/Systemd-start/).

[UWSM](https://github.com/Vladimir-csp/uwsm) (Universal Wayland Session
Manager) runs the compositor in systemd units and manages the session
environment and applications.

### Installation

```sh
sudo pacman -S uwsm libnewt
```

### Launch from TTY

This dotfiles setup installs the following logic in `~/.zprofile`, so it runs
only for a login shell attached to a terminal:

#### Option A: Interactive selection menu at login

```zsh
if [[ -o login && -t 0 ]] && command -v uwsm >/dev/null 2>&1; then
    if uwsm check may-start && uwsm select; then
        exec uwsm start default
    fi
fi
```

#### Option B: Direct launch

```zsh
if [[ -o login && -t 0 ]] && command -v uwsm >/dev/null 2>&1; then
    if uwsm check may-start; then
        exec uwsm start hyprland.desktop
    fi
fi
```

_Note: For display managers, select `Hyprland (uwsm-managed)`._

### Application Launching

Launch graphical applications as Systemd scopes:

```sh
uwsm app -- alacritty
```

### Autostart

- **XDG Autostart**: Handled automatically by the Systemd session target.
- **Native User Services**:
  ```sh
  systemctl --user enable <service>
  # If the service lacks an [Install] section:
  systemctl --user add-wants graphical-session.target <service>
  ```

## Real-time audio scheduling

The `realtime-privileges` package sets PAM limits and creates a `realtime`
group for real-time scheduling. This can help prevent audio dropouts under high
CPU load.

Install the package and add your user to the group:

```sh
sudo pacman -S realtime-privileges
```

```sh
sudo usermod -aG realtime MyUser
```

Log out and back in, or reboot, for the new group membership to take effect.

## Security follow-up

Security settings depend on how the machine is used and who can access it.
Consult the [ArchWiki security recommendations](https://wiki.archlinux.org/title/Security)
for current guidance on networking, remote access, updates, Secure Boot, and
backups. Keep an independently stored backup of the LUKS header and recovery
material; do not store the only copy on the encrypted disk.
