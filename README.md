# My dotfiles

Configuration used on my [Arch Linux](https://archlinux.org/) with i3 / i3status

## Hyprland

### Wallpaper

Put wallpaper into your `~/.local/share/backgrounds` folder

You can batch this with exiftool :

```sh
exiftool -q -if '$Keywords =~ /paysage/' -r ${SRC_DIR} -o "${XDG_DATA_HOME}/backgrounds/"
```

## i3

![screenshot](https://gitlab.com/pad92/dotfiles/-/raw/main/dist/arch/screenshot-i3.png)

## sway
![screenshot](https://gitlab.com/pad92/dotfiles/-/raw/main/dist/arch/screenshot-sway.png)

# Install Dotfile

```sh
git clone https://gitlab.com/pad92/dotfiles.git ~/.dotfiles
./.dotfiles/install
```

## Install only VIM

```sh
curl -sSL https://gitlab.com/pad92/dotfiles/-/raw/main/vim.sh | sh
```

# ArchLinux

## My Setup

- [install.md](https://gitlab.com/pad92/dotfiles/-/blob/main/dist/arch/install.md)
- [pkglist.txt](https://gitlab.com/pad92/dotfiles/-/tree/main/dist/arch/packages/)

# Ubuntu

## My Setup

- [install.md](https://gitlab.com/pad92/dotfiles/-/raw/main/dist/ubuntu/install.sh)
