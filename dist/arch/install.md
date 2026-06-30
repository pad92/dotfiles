# Arch Linux Full-Disk Encryption Installation Guide

This guide provides instructions for an Arch Linux installation featuring full-disk encryption via LVM on LUKS and an encrypted boot partition (GRUB) for UEFI systems.

For advanced security, the system can be further hardened against Evil Maid attacks using UEFI Secure Boot with custom enrolled keys and a self-signed kernel/bootloader.

## 📖 Preface

You will find most of this information pulled from the [Arch Wiki](<https://wiki.archlinux.org/index.php/Dm-crypt/Encrypting_an_entire_system#Encrypted_boot_partition_(GRUB)>) and other resources linked thereof.

Based on [huntrar's gist](https://gist.github.com/huntrar/e42aee630bee3295b2c671d098c81268#file-full-disk-encryption-arch-uefi-md) installation guide.

_Note:_ The system was installed on an NVMe SSD, substitute `/dev/nvme0nX` with `/dev/sdX` or your device as needed.

Modern Arch Linux installations often use the `archinstall` tool for streamlined setup. This guide represents a manual approach to achieve the same result, which can be useful for understanding the underlying process or for systems where automated tools aren't available.

## 🗂️ Table of contents

[[_TOC_]]

# 💿 Create USB stick

- Download ISO From [https://archlinux.org/download/](http://archlinux.mirrors.ovh.net/archlinux/iso/latest/)

```sh
wget http://archlinux.mirrors.ovh.net/archlinux/iso/latest/archlinux-x86_64.iso
wget http://archlinux.mirrors.ovh.net/archlinux/iso/latest/archlinux-x86_64.iso.sig

gpg --keyserver pgp.mit.edu --keyserver-options auto-key-retrieve --verify archlinux-x86_64.iso.sig

sudo dd bs=4M if=archlinux-*.iso of=/dev/sda status=progress oflag=sync
```

where `/dev/sda` is your usb key

# 🐧 From live

| Number | Start (sector) | End (sector) | Size       | Code | Name                |
| ------ | -------------- | ------------ | ---------- | ---- | ------------------- |
| 1      | 2048           | 4095         | 1024.0 KiB | EF02 | BIOS boot partition |
| 2      | 4096           | 1130495      | 550.0 MiB  | EF00 | EFI System          |
| 3      | 1130496        | 976773134    | 465.2 GiB  | 8309 | Linux LUKS          |

## 💽 Partitions

### ➕ Create

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

### 🔒 luks

```sh
cryptsetup luksFormat --type luks1 --use-random -S 1 -s 512 -h sha512 -i 5000 /dev/nvme0n1p3
cryptsetup luksOpen /dev/nvme0n1p3 cryptlvm
```

### 🧱 lvm

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

### 🗄️ Format

```sh
mkfs.fat -F32 /dev/nvme0n1p2                     -n EFI
mkfs.ext4     /dev/mapper/archlvm-slash          -L slash
mkfs.ext4     /dev/mapper/archlvm-home           -L home
mkfs.ext4     /dev/mapper/archlvm-opt            -L opt
mkfs.ext4     /dev/mapper/archlvm-var_lib_docker -L var_lib_docker
mkswap        /dev/mapper/archlvm-swap           -L swap
swapon        /dev/mapper/archlvm-swap
```

### 📂 Mount

```sh
mount /dev/mapper/archlvm-slash /mnt
mkdir /mnt/efi /mnt/home /mnt/var/lib/docker /mnt/opt -p
mount /dev/nvme0n1p2                     /mnt/efi
mount /dev/mapper/archlvm-home           /mnt/home
mount /dev/mapper/archlvm-var_lib_docker /mnt/var/lib/docker
mount /dev/mapper/archlvm-opt            /mnt/opt
chmod 700 /boot
```

## ⚙️ System

### 📦 Install base

```sh
# Available kernel options:
# KERNEL='linux'     # Vanilla Linux kernel and modules, with a few patches applied.
# KERNEL='linux-lts' # Long-term support (LTS) Linux kernel and modules.
# KERNEL='linux-zen' # Result of a collaborative effort of kernel hackers to provide the best Linux kernel possible for everyday systems.
# KERNEL='linux-hardened' # Security-focused kernel with additional hardening features

# Modern archinstall typically recommends 'linux' for most users
KERNEL='linux'

# Available microcode options:
# UCODE='intel-ucode' # for Intel processors.
# UCODE='amd-ucode'   # for AMD processors.

UCODE='intel-ucode' # for Intel processors, adjust as needed

pacstrap /mnt \
  base \
  base-devel \
  ${KERNEL} \
  ${KERNEL}-headers \
  ${UCODE} \
  crda \
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
  resolvconf \
  rsync \
  terminus-font \
  vim \
  wpa_supplicant \
  zsh
```

### 🌐 Configure resolv.conf

```sh
echo '[main]
rc-manager=resolvconf' > /mnt/etc/NetworkManager/conf.d/rc-manager.conf
```

### 📶 Configure wifi

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

### 🔊 Sound

```sh
if grep -wq '^snd_had_intel' /proc/modules; then
echo "options snd_had_intel power_save=1" > /mnt/etc/modprobe.d/audio_powersave.conf
elif grep -wq '^snd_ac97_codec' /proc/modules; then
echo "options snd_ac97_codec power_save=1" > /mnt/etc/modprobe.d/audio_powersave.conf
fi
```

### 🗃️ Create fstab

```sh
genfstab -U /mnt                                           >> /mnt/etc/fstab
echo 'tmpfs     /tmp tmpfs defaults,noatime,mode=1777 0 0' >> /mnt/etc/fstab
sed -i 's/relatime/noatime/g' /mnt/etc/fstab
```

# 📦 From chroot

```sh
arch-chroot /mnt
```

At this point you should have the following partitions and logical volumes:
`lsblk`

| NAME                         | MAJ:MIN | RM  | SIZE   | RO  | TYPE  | MOUNTPOINT      |
| ---------------------------- | ------- | --- | ------ | --- | ----- | --------------- |
| nvme0n1                      | 259:0   | 0   | 953.9G | 0   | disk  |                 |
| ├─nvme0n1p1                  | 259:1   | 0   | 1M     | 0   | part  |                 |
| ├─nvme0n1p2                  | 259:2   | 0   | 550M   | 0   | part  | /efi            |
| ├─nvme0n1p3                  | 259:3   | 0   | 953.3G | 0   | part  |                 |
| ..└─cryptlvm                 | 254:0   | 0   | 953.3G | 0   | crypt |                 |
| ....├─archlvm-swap           | 254:1   | 0   | 31.1G  | 0   | lvm   | [SWAP]          |
| ....├─archlvm-slash          | 254:2   | 0   | 32G    | 0   | lvm   | /               |
| ....└─archlvm-home           | 254:3   | 0   | 100G   | 0   | lvm   | /home           |
| ....└─archlvm-opt            | 254:4   | 0   | 30G    | 0   | lvm   | /opt            |
| ....└─archlvm-var_lib_docker | 254:5   | 0   | 10G    | 0   | lvm   | /var/lib/docker |

## 🛠️ makeflags

use all core for builds

```sh
sed -i 's/^CXXFLAGS.*/CXXFLAGS="-march=native -mtune=native -O2 -pipe -fstack-protector-strong --param=ssp-buffer-size=4 -fno-plt"/' /etc/makepkg.conf && \
sed -i 's/^#RUSTFLAGS.*/RUSTFLAGS="-C opt-level=2 -C target-cpu=native"/' /etc/makepkg.conf && \
sed -i 's/^#BUILDDIR.*/BUILDDIR=\/tmp\/makepkg/' /etc/makepkg.conf && \
sed -i 's/^#MAKEFLAGS.*/MAKEFLAGS="-j$(getconf _NPROCESSORS_ONLN) --quiet"/' /etc/makepkg.conf && \
sed -i 's/^COMPRESSGZ.*/COMPRESSGZ=(pigz -c -f -n)/' /etc/makepkg.conf && \
sed -i 's/^COMPRESSBZ2.*/COMPRESSBZ2=(pbzip2 -c -f)/' /etc/makepkg.conf && \
sed -i 's/^COMPRESSXZ.*/COMPRESSXZ=(xz -T "$(getconf _NPROCESSORS_ONLN)" -c -z --best -)/' /etc/makepkg.conf && \
sed -i 's/^COMPRESSZST.*/COMPRESSZST=(zstd -c -z -q --ultra -T0 -22 -)/' /etc/makepkg.conf && \
sed -i 's/^COMPRESSLZ.*/COMPRESSLZ=(lzip -c -f)/' /etc/makepkg.conf && \
sed -i 's/^COMPRESSLRZ.*/COMPRESSLRZ=(lrzip -9 -q)/' /etc/makepkg.conf && \
sed -i 's/^COMPRESSLZO.*/COMPRESSLZO=(lzop -q --best)/' /etc/makepkg.conf && \
sed -i 's/^COMPRESSZ.*/COMPRESSZ=(compress -c -f)/' /etc/makepkg.conf && \
sed -i 's/^COMPRESSLZ4.*/COMPRESSLZ4=(lz4 -q --best)/' /etc/makepkg.conf
```

## 🕐 Time zone

```sh
timedatectl set-timezone "$(curl -s --fail https://ipapi.co/timezone)"
timedatectl set-ntp true
timedatectl
hwclock --systohc
```

## 🌍 locales

```sh
sed -i 's/^#fr_FR/fr_FR/g' /etc/locale.gen
sed -i 's/^#en_US/en_US/g' /etc/locale.gen
locale-gen
echo 'LANG=en_US.UTF-8'  > /etc/locale.conf
```

## ⌨️ keymap

```sh
echo 'KEYMAP=us-acentos' > /etc/vconsole.conf
echo 'FONT=ter-116n'    >> /etc/vconsole.conf

mkdir -p /etc/X11/xorg.conf.d
cat <<EOF>/etc/X11/xorg.conf.d/00-keyboard.conf
# Read and parsed by systemd-located. It's probably wise not to edit this file
# manually too freely.
Section "InputClass"
        Identifier "system-keyboard"
        MatchIsKeyboard "on"
        Option "XkbLayout" "us"
        Option "XkbVariant" "intl"
EndSection
EOF
```

## 🏷️ hostname

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

## 🥾 boot

### 🧰 Grub

```sh
UUID=$(blkid /dev/nvme0n1p3 -s UUID -o value)

sed -i "/^GRUB_CMDLINE_LINUX=/cGRUB_CMDLINE_LINUX=\"cryptdevice=UUID=${UUID}:cryptlvm root=/dev/mapper/archlvm-slash cryptkey=rootfs:/root/.cryptlvm/archluks.bin\""  /etc/default/grub

sed -i "/GRUB_ENABLE_CRYPTODISK=/cGRUB_ENABLE_CRYPTODISK=y" /etc/default/grub

grub-install --target=x86_64-efi --efi-directory=/efi --bootloader-id=ArchLinux
grub-mkconfig -o /boot/grub/grub.cfg
```

### 🧬 initramfs

```sh
mkdir /root/.cryptlvm && chmod 700 /root/.cryptlvm
head -c 64 /dev/urandom > /root/.cryptlvm/archluks.bin && chmod 600 /root/.cryptlvm/archluks.bin
# Note: -i 1 sets the PBKDF iterations time to 1ms for faster boot. Increase for stronger security.
cryptsetup -v luksAddKey -i 1 /dev/nvme0n1p3 /root/.cryptlvm/archluks.bin

# For Intel graphics; for AMD use: MODULES=(amdgpu), for Nvidia use: MODULES=(nvidia nvidia_modeset nvidia_uvm nvidia_drm)
sed -i '/^MODULES/c\MODULES=(intel_agp i915)' /etc/mkinitcpio.conf
sed -i '/^FILES/c\FILES=(/root/.cryptlvm/archluks.bin)' /etc/mkinitcpio.conf
sed -i '/^HOOKS/c\HOOKS=(base udev autodetect modconf block keyboard keymap consolefont encrypt lvm2 filesystems fsck)' /etc/mkinitcpio.conf
mkinitcpio -P
```

## 🛎️ services

```sh
systemctl enable NetworkManager
systemctl enable systemd-timesyncd.service
```

## 👤 user

```sh
MYUSER='MyUser'
useradd -m -s /bin/zsh -G network,users,storage,lp,input,audio,wheel ${MYUSER}
echo '%wheel ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers.d/wheel
passwd ${MYUSER}
```

### 📁 dotfiles

```sh
# Run setup commands in user context without blocking shell execution
sudo -u ${MYUSER} -i bash -c '
  git clone https://gitlab.com/pad92/dotfiles.git ~/.dotfiles
  mkdir -p ~/.config
  ~/.dotfiles/install
'


```

### 📦 Packages manager

```sh
# Enable color, checksum, and verbose output in pacman
sed -i 's/#Color/Color/' /etc/pacman.conf && \
sed -i 's/#CheckSpace/CheckSpace/' /etc/pacman.conf && \
sed -i 's/#UseSyslog/UseSyslog/' /etc/pacman.conf

# Enable multilib repository for 32-bit application support
# Uncomment the following lines in /etc/pacman.conf:
# [multilib]
# SigLevel = PackageRequired
# Include = /etc/pacman.d/mirrorlist

# Modern archinstall typically enables these repositories and settings automatically
# For now, we'll leave the multilib configuration as a commented example
# Uncomment the multilib section manually if needed
```

### 🏗️ aur

```sh
# Modern archinstall typically handles AUR package management automatically
# For manual installation, 'yay' is a popular choice for AUR packages

# Install yay (AUR helper)
sudo pacman -Sy --noconfirm git base-devel
git clone https://aur.archlinux.org/yay.git
cd yay
makepkg -si --noconfirm
cd
rm -fr yay

# Alternative AUR helpers:
# - paru (more lightweight)
# - pikaur (Python-based)
# - pamac (GUI-based, if using a desktop environment)
```

### 🪟 WM and softs

The system packages and software environment are automatically installed during the dotfiles setup script (`~/.dotfiles/install`) via an interactive, high-fidelity menu.

However, if you wish to manually install or re-install the packages later, you can run:

```sh
yay -S --needed $(cat ~/.dotfiles/dist/arch/packages/*.txt)
```

Alternatively, you can re-run the dotfiles installer at any time:

```sh
~/.dotfiles/install
```

```sh
exit
```

```sh
sync
exit
umount -R /mnt
reboot
```

# ✨ Optional

## ⚡ Auto CPUfreq

```sh
sudo systemctl enable --now auto-cpufreq
```

## ✂️ SSD Trim

```sh
sudo pacman -S util-linux
sudo systemctl enable fstrim.timer
```

## 🛡️ USBGuard

```sh
yay -S usbguard usbguard-applet-qt
sudo usbguard generate-policy | sudo tee /etc/usbguard/rules.conf
sudo systemctl start usbguard.service
sudo systemctl enable usbguard.service
```

## 🐳 Docker

```sh
yay -S docker docker-compose
usermod -a -G docker MyUser
```

## 🎮 Nvidia

```sh
sed -i '/^MODULES/c\MODULES=(nvidia)' /etc/mkinitcpio.conf
yay -S nvidia-dkms nvidia-utils
sudo mkinitcpio -P

```

## 🔀 Nvidia Prime

```sh
yay -S nvidia-dkms nvidia-utils nvidia-prime
```

## 🎵 Spotify

Remove notification

```sh
echo 'ui.track_notifications_enabled=false' > ~/.config/spotify/Users/*-user/prefs
```

## 🔑 GNOME Keyring PAM Setup

Add `pam_gnome_keyring.so` to `/etc/pam.d/login` to automatically unlock GNOME Keyring on TTY login:

```ini
#%PAM-1.0

auth       requisite    pam_nologin.so
auth       include      system-local-login
-auth      optional     pam_gnome_keyring.so
account    include      system-local-login
password   include      system-local-login
-password  optional     pam_gnome_keyring.so    use_authtok
session    include      system-local-login
-session   optional     pam_gnome_keyring.so    auto_start
```

## 🚀 Systemd Startup (UWSM)

For complete documentation, see [Hyprland Wiki](https://wiki.hypr.land/Useful-Utilities/Systemd-start/).

[UWSM](https://github.com/Vladimir-csp/uwsm) (Universal Wayland Session Manager) wraps the compositor in Systemd units for robust environment, application, and session management.

### 📥 Installation

```sh
sudo pacman -S uwsm libnewt
```

### 🖥️ Launch from TTY

Add to your shell configuration (note that this is already integrated at the bottom of `~/.zshrc` in this dotfiles setup, but you can use `~/.zprofile` instead if you prefer to create and configure one):

#### 🅰️ Option A: Interactive selection menu at login

```zsh
if uwsm check may-start && uwsm select; then
    exec uwsm start default
fi
```

#### 🅱️ Option B: Direct launch

```zsh
if uwsm check may-start; then
    exec uwsm start hyprland.desktop
fi
```

_Note: For display managers, select `Hyprland (uwsm-managed)`._

### ▶️ Application Launching

Launch graphical applications as Systemd scopes:

```sh
uwsm app -- alacritty
```

### 🔄 Autostart

- **XDG Autostart**: Handled automatically by the Systemd session target.
- **Native User Services**:
  ```sh
  systemctl --user enable <service>
  # If the service lacks an [Install] section:
  systemctl --user add-wants graphical-session.target <service>
  ```

## 🎧 Real-time Audio & Latency (Gaming/Work/VoIP)

To allow PipeWire and WirePlumber to run with real-time scheduling (preventing audio stuttering, clicks, and dropouts under heavy CPU load, such as in games or during compilation on a work machine):

1. Install the `realtime-privileges` package, which configures the necessary PAM limits and creates the `realtime` group:

```sh
sudo pacman -S realtime-privileges
```

2. Add your user to the `realtime` group:

```sh
sudo usermod -aG realtime MyUser
```

_Note: You must log out and log back in (or reboot) for the group membership to take effect. If you don't do this, PipeWire logs will show `mod.rt: could not set nice-level to -11: Permission denied`._

## 🔐 Modern Security Practices

Modern Arch Linux installations using tools like `archinstall` typically include additional security measures:

- **Enable and configure firewalld** for network protection
- **Install and configure fail2ban** to prevent brute-force attacks
- **Set up automatic security updates** using tools like `pacman-contrib` and `reflector`
- **Configure secure SSH settings** (disable root login, use key-based authentication only)
- **Enable systemd-boot** as an alternative bootloader to GRUB (though GRUB is still widely used)
- **Consider using a more secure initramfs configuration** with additional encryption layers
- **Implement proper backup strategies** for the LUKS keyfiles and critical system data

These practices enhance system security beyond the basic installation and are recommended for production systems.
