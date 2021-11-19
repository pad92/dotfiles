# Create USB stick

- Download ISO From [https://archlinux.org/download/](https://mirrors.eric.ovh/arch/iso/latest/)
```
sudo dd bs=4M if=archlinux-*.iso of=/dev/sda status=progress oflag=sync
```

where /dev/sda is your usb key

# From live
```
gdisk /dev/nvme0n1
o
Y

n
[enter]
[enter]
+550M
ef00

n
[enter]
[enter]
[enter]
8309

w
Y
```

|#|size |type|
|-|-----|----|
|1|+550M|ef00|
|2|     |8309|

```
mkfs.vfat -F32 -n EFI /dev/nvme0n1p1
cryptsetup luksFormat /dev/nvme0n1p2
cryptsetup luksOpen /dev/nvme0n1p2 slash
mkfs.ext4 -L slash /dev/mapper/slash

mount /dev/mapper/slash /mnt
mkdir /mnt/boot
mount /dev/nvme0n1p1 /mnt/boot

pacstrap /mnt base linux linux-firmware lvm2 intel-ucode vim base-devel terminus-font network-manager-applet networkmanager wpa_supplicant openssh git python zsh neofetch rsync crda

echo 'WIRELESS_REGDOM="FR"' > /mnt/etc/conf.d/wireless-regdom

genfstab -U /mnt >> /mnt/etc/fstab
echo 'tmpfs /tmp tmpfs defaults,noatime,mode=1777 0 0' >> /mnt/etc/fstab
sed -i 's/relatime/noatime/g' /mnt/etc/fstab
```

# From chroot

```
arch-chroot /mnt

ln -sf /usr/share/zoneinfo/Europe/Paris /etc/localtime
hwclock --systohc

sed -i 's/^#fr_FR/fr_FR/g' /etc/locale.gen
sed -i 's/^#en_US/en_US/g' /etc/locale.gen
locale-gen

echo 'LANG=en_US.UTF-8'  > /etc/locale.conf
echo 'KEYMAP=us-acentos' > /etc/vconsole.conf
echo 'FONT=ter-116n'    >> /etc/vconsole.conf

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

myhostname='MyArch'
echo "$myhostname" > /etc/hostname
cat <<EOF>> /etc/hosts
127.0.0.1  localhost
127.0.1.1  $myhostname
::1        localhost ip6-localhost ip6-loopback
ff02::1    ip6-allnodes
ff02::2    ip6-allrouters
EOF

sed -i '/^MODULES/c\MODULES="intel_agp i915"' /etc/mkinitcpio.conf
sed -i '/^HOOKS/c\HOOKS="base udev autodetect modconf block keyboard keymap consolefont encrypt filesystems fsck"' /etc/mkinitcpio.conf
mkinitcpio -P

bootctl --path=/boot install
echo 'default arch'    > /boot/loader/loader.conf
echo 'console-mode 1' >> /boot/loader/loader.conf
echo 'timeout 3'      >> /boot/loader/loader.conf

UUID=$(blkid /dev/nvme0n1p2 -s UUID -o value)
echo 'title Arch Linux'                                                  > /boot/loader/entries/arch.conf
echo 'linux /vmlinuz-linux'                                             >> /boot/loader/entries/arch.conf
echo 'initrd /intel-ucode.img'                                          >> /boot/loader/entries/arch.conf
echo 'initrd /initramfs-linux.img'                                      >> /boot/loader/entries/arch.conf
echo "options cryptdevice=UUID=${UUID}:slash root=/dev/mapper/slash rw quiet splash vt.global_cursor_default=0" >> /boot/loader/entries/arch.conf

systemctl enable NetworkManager
systemctl enable sshd

vim /etc/pacman.conf
# Color
# ILoveCandy
# [multilib]
# SigLevel = PackageRequired
# Include = /etc/pacman.d/mirrorlist


passwd

useradd -m -s /bin/zsh -G network,users,storage,lp,input,audio,wheel MyUser
echo '%wheel ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers.d/wheel
passwd MyUser

sync
exit
umount -R /mnt
reboot
```

```
sudo pacman -Syy
git clone https://aur.archlinux.org/yay.git
cd yay
makepkg -si
cd
rm -fr yay

git clone https://github.com/pad92/dotfiles.git ~/.dotfiles
mkdir ~/.config
~/.dotfiles/install

echo

cat <<EOF> ~/.config/nitrogen/bg-saved.cfg
[xin_-1]
file=/usr/share/backgrounds/archlinux/geolanes.png
mode=4
bgcolor=#000000
EOF

yay -S $(cat ~/.dotfiles/archlinux/pkglist.txt)

flatpak install com.microsoft.Teams \
                com.spotify.Client \
                org.signal.Signal

sudo systemctl enable gdm
```

## Plymouth

```
sudo sed -i '/^HOOKS/c\HOOKS="base udev plymouth autodetect modconf block keyboard keymap consolefont plymouth-encrypt filesystems fsck"' /etc/mkinitcpio.conf
yay -S plymouth gdm-plymouth plymouth-theme-dark-arch
sudo plymouth-set-default-theme -R dark-arch
```
