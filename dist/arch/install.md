# Arch Linux Full-Disk Encryption Installation Guide
This guide provides instructions for an Arch Linux installation featuring full-disk encryption via LVM on LUKS and an encrypted boot partition (GRUB) for UEFI systems.

Following the main installation are further instructions to harden against Evil Maid attacks via UEFI Secure Boot custom key enrollment and self-signed kernel and bootloader.

## Preface
You will find most of this information pulled from the [Arch Wiki](https://wiki.archlinux.org/index.php/Dm-crypt/Encrypting_an_entire_system#Encrypted_boot_partition_(GRUB)) and other resources linked thereof.

Based on [huntrar's gist](https://gist.github.com/huntrar/e42aee630bee3295b2c671d098c81268#file-full-disk-encryption-arch-uefi-md) installation guide.


*Note:* The system was installed on an NVMe SSD, substitute ```/dev/nvme0nX``` with ```/dev/sdX``` or your device as needed.

## Table of contents
[[_TOC_]]

# Create USB stick

- Download ISO From [https://archlinux.org/download/](http://archlinux.mirrors.ovh.net/archlinux/iso/latest/)

```
wget -r -nd --no-parent -A 'archlinux-*-x86_64.iso'     http://archlinux.mirrors.ovh.net/archlinux/iso/latest/
wget -r -nd --no-parent -A 'archlinux-*-x86_64.iso.sig' http://archlinux.mirrors.ovh.net/archlinux/iso/latest/

gpg --keyserver pgp.mit.edu --keyserver-options auto-key-retrieve --verify archlinux-*-x86_64.iso.sig

sudo dd bs=4M if=archlinux-*.iso of=/dev/sda status=progress oflag=sync
```

where /dev/sda is your usb key

# From live

Number | Start (sector) | End (sector) |    Size    | Code |        Name         |
-------|----------------|--------------|------------|------|---------------------|
   1   |   2048         |   4095       | 1024.0 KiB | EF02 | BIOS boot partition |
   2   |   4096         |   1130495    | 550.0 MiB  | EF00 | EFI System          |
   3   |   1130496      |   976773134  | 465.2 GiB  | 8309 | Linux LUKS          |

## Partitions
### Create
```
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


### luks
```
cryptsetup luksFormat --type luks1 --use-random -S 1 -s 512 -h sha512 -i 5000 /dev/nvme0n1p3
cryptsetup luksOpen /dev/nvme0n1p3 cryptlvm
```

### lvm
```
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
```
mkfs.fat -F32 /dev/nvme0n1p2                     -n EFI
mkfs.ext4     /dev/mapper/archlvm-slash          -L slash
mkfs.ext4     /dev/mapper/archlvm-home           -L home
mkfs.ext4     /dev/mapper/archlvm-opt            -L opt
mkfs.ext4     /dev/mapper/archlvm-var_lib_docker -L var_lib_docker
mkswap        /dev/mapper/archlvm-swap           -L swap
swapon        /dev/mapper/archlvm-swap
```

### Mount

```
mount /dev/mapper/archlvm-slash /mnt
mkdir /mnt/efi /mnt/home /mnt/var/lib/docker /mnt/opt -p
mount /dev/nvme0n1p2                     /mnt/efi
mount /dev/mapper/archlvm-home           /mnt/home
mount /dev/mapper/archlvm-var_lib_docker /mnt/var/lib/docker
mount /dev/mapper/archlvm-opt            /mnt/opt
chmod 700 /boot
```

## System
### Install base
```
KERNEL='linux'     # Vanilla Linux kernel and modules, with a few patches applied.
KERNEL='linux-lts' # Long-term support (LTS) Linux kernel and modules.
KERNEL='linux-zen' # Result of a collaborative effort of kernel hackers to provide the best Linux kernel possible for everyday systems.

UCODE='intel-ucode' # for Intel processors.
UCODE='amd-ucode'   # for AMD processors

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
  linux-firmware \
  lvm2 \
  neofetch \
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

### Configure resolv.conf
```
echo '[main]
rc-manager=resolvconf' > /etc/NetworkManager/conf.d/rc-manager.conf
```

### Configure wifi region
```
echo 'WIRELESS_REGDOM="FR"' > /mnt/etc/conf.d/wireless-regdom
```
### Create fstab
```
genfstab -U /mnt                                           >> /mnt/etc/fstab
echo 'tmpfs     /tmp tmpfs defaults,noatime,mode=1777 0 0' >> /mnt/etc/fstab
sed -i 's/relatime/noatime/g' /mnt/etc/fstab
```

# From chroot

```
arch-chroot /mnt
```

At this point you should have the following partitions and logical volumes:
```lsblk```

NAME                          | MAJ:MIN | RM  |  SIZE  | RO  | TYPE  | MOUNTPOINT      |
------------------------------|---------|-----|--------|-----|-------|-----------------|
nvme0n1                       |  259:0  |  0  | 953.9G |  0  | disk  |                 |
├─nvme0n1p1                   |  259:1  |  0  |     1M |  0  | part  |                 |
├─nvme0n1p2                   |  259:2  |  0  |   550M |  0  | part  | /efi            |
├─nvme0n1p3                   |  259:3  |  0  | 953.3G |  0  | part  |                 |
..└─cryptlvm                  |  254:0  |  0  | 953.3G |  0  | crypt |                 |
....├─archlvm-swap            |  254:1  |  0  |  31.1G |  0  | lvm   | [SWAP]          |
....├─archlvm-root            |  254:2  |  0  |    32G |  0  | lvm   | /               |
....└─archlvm-home            |  254:3  |  0  |   100G |  0  | lvm   | /home           |
....└─archlvm-opt             |  254:4  |  0  |    30G |  0  | lvm   | /opt            |
....└─archlvm-var_lib_docker  |  254:5  |  0  |    10G |  0  | lvm   | /var/lib/docker |


## makeflags

use all core for builds

```
sed -i "/MAKEFLAGS=/cMAKEFLAGS=\"-j $((`nproc`+1))\"" /etc/makepkg.conf
```

## Time zone
```
timedatectl set-timezone "$(curl -s --fail https://ipapi.co/timezone)"
timedatectl set-ntp true
timedatectl
hwclock --systohc
```

## locales
```
sed -i 's/^#fr_FR/fr_FR/g' /etc/locale.gen
sed -i 's/^#en_US/en_US/g' /etc/locale.gen
locale-gen
echo 'LANG=en_US.UTF-8'  > /etc/locale.conf
```

## keymap
```
echo 'KEYMAP=us-acentos' > /etc/vconsole.conf
echo 'FONT=ter-116n'    >> /etc/vconsole.conf

mkdir -p /etc/X11/xorg.conf.d
cat <<EOF>/etc/X11/xorg.conf.d/00-keyboard.conf
# Read and parsed by systemd-localed. It's probably wise not to edit this file
# manually too freely.
Section "InputClass"
        Identifier "system-keyboard"
        MatchIsKeyboard "on"
        Option "XkbLayout" "us"
        Option "XkbVariant" "intl"
EndSection
EOF
```

## hostname
```
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

## boot
### Grub
```
UUID=$(blkid /dev/nvme0n1p3 -s UUID -o value)

sed -i "/^GRUB_CMDLINE_LINUX=/cGRUB_CMDLINE_LINUX=\"cryptdevice=UUID=${UUID}:cryptlvm root=/dev/mapper/archlvm-slash cryptkey=rootfs:/root/.cryptlvm/archluks.bin\""  /etc/default/grub

sed -i "/GRUB_ENABLE_CRYPTODISK=/cGRUB_ENABLE_CRYPTODISK=y" /etc/default/grub

grub-install --target=x86_64-efi --efi-directory=/efi --bootloader-id=ArchLinux
grub-mkconfig -o /boot/grub/grub.cfg
```

### initramfs
```
mkdir /root/.cryptlvm && chmod 700 /root/.cryptlvm
head -c 64 /dev/urandom > /root/.cryptlvm/archluks.bin && chmod 600 /root/.cryptlvm/archluks.bin
cryptsetup -v luksAddKey -i 1 /dev/nvme0n1p3 /root/.cryptlvm/archluks.bin

sed -i '/^MODULES/c\MODULES=(intel_agp i915)' /etc/mkinitcpio.conf
sed -i '/^FILES/c\FILES=(/root/.cryptlvm/archluks.bin)' /etc/mkinitcpio.conf
sed -i '/^HOOKS/c\HOOKS=(base udev autodetect modconf block keyboard keymap consolefont encrypt lvm2 filesystems fsck)' /etc/mkinitcpio.conf
mkinitcpio -P
```

## services
```
systemctl enable NetworkManager
systemctl enable systemd-timesyncd.service
```

## user
```
MYUSER='MyUser'
useradd -m -s /bin/zsh -G network,users,storage,lp,input,audio,wheel ${MYUSER}
echo '%wheel ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers.d/wheel
passwd ${MYUSER}
```
### dotfiles
```
su - ${MYUSER}
git clone https://gitlab.com/pad92/dotfiles.git ~/.dotfiles
mkdir ~/.config
~/.dotfiles/install

cat <<EOF> ~/.config/nitrogen/bg-saved.cfg
[xin_-1]
file=/usr/share/backgrounds/archlinux/geolanes.png
mode=4
bgcolor=#000000
EOF
```

### Packages manager
```
sudo vim /etc/pacman.conf
# Color
# ILoveCandy
# [multilib]
# SigLevel = PackageRequired
# Include = /etc/pacman.d/mirrorlist
```

### aur
```
sudo pacman -Sy

git clone https://aur.archlinux.org/yay.git
cd yay
makepkg -si
cd
rm -fr yay
```

### WM and softs
```
yay -S --needed $(cat ~/.dotfiles/dist/archlinux/packages/*.txt)

exit
```

```
sync
exit
umount -R /mnt
reboot
```
# Optional

## SSD Trim

```
sudo pacman -S util-linux
sudo systemctl enable fstrim.timer
```

## USBGuard
```
yay -S usbguard usbguard-applet-qt
sudo usbguard generate-policy | sudo tee /etc/usbguard/rules.conf
sudo systemctl start usbguard.service
sudo systemctl enable usbguard.service
```

## Flatpak Apps
```
flatpak install com.microsoft.Teams \
                org.signal.Signal
```

## Docker
```
yay -S docker docker-compose
usermod -a -G docker MyUser
```

## Nvidia
```
sed -i '/^MODULES/c\MODULES=(nvidia)' /etc/mkinitcpio.conf
yay -S nvidia-dkms nvidia-utils
sudo mkinitcpio -P

```

## Nvidia Prime
```
yay -S nvidia-dkms nvidia-utils nvidia-prime
```

## Spotify
Remove notification
```
echo 'ui.track_notifications_enabled=false' > ~/.config/spotify/Users/*-user/prefs
```
