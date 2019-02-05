#/bin/sh

# === INIT ===
BIN_DEPS='git'

# === CHECKS ===
for BIN in $BIN_DEPS; do
  which $BIN 1>/dev/null 2>&1
  if [ $? -ne 0 ]; then
    echo "Error: Required file could not be found: $BIN"
    exit 1
  fi
done

# === DO ===
if [ -d ~/.dotfiles ]; then
  git pull ~/.dotfiles/
else
  git clone --recursive http://git.depad.fr/pascal/dotfiles.git ~/.dotfiles
fi

DOTFILES='.zshrc .screenrc .byobu .vimrc .vim .tmux.conf .tmux .fonts .themes .icons .dir_colors'
for DOTFILE in $DOTFILES; do
  if [ ! -L ${HOME}/$DOTFILE ]; then
    ln -sf ${HOME}/.dotfiles/$DOTFILE ${HOME}/$DOTFILE
  fi
done

CONFFILES='rofi sway terminator termite tint2 waybar'
for CONFFILE in $CONFFILES; do
  if [ ! -L ${HOME}/.config/$CONFFILE ]; then
    ln -sf ${HOME}/.dotfiles/.config/$CONFFILE ${HOME}/.config/$CONFFILE
  fi
done

if which apt-get 1>/dev/null 2>&1 ; then
  if [ "$(id -u)" != "0" ]; then
    sudo add-apt-repository ppa:daniruiz/flat-remix
    sudo apt-get install python python-new t screenfetch flat-remix-gnome flat-remix flat-remix-gtk
  else 
    add-apt-repository ppa:daniruiz/flat-remix
    apt-get install python python-newt sc reenfetch flat-remix-gnome flat-remix flat-remix-gtk
  fi
else
  if [ "$(id -u)" != "0" ]; then
    sudo dnf copr enable daniruiz/flat-remix
    sudo dnf install newt tilix-nautilus  tilix screenfetch flat-remix-gnome flat-remix flat-remix-gtk
  else
    dnf copr enable daniruiz/flat-remix 
    dnf newt tilix-nautilus tilix screenfetch flat-remix-gnome flat-remix flat-remix-gtk
  fi
fi
vim +PluginInstall +qall

dconf load /com/gexperts/Tilix/ < tilix.dconf

if which gsettings 1>/dev/null 2>&1 ; then
  gsettings set org.gnome.shell.extensions.user-theme name "Flat-Remix-Dark";
  gsettings set org.gnome.desktop.interface icon-theme "Flat-Remix-Dark"
  gsettings set org.gnome.desktop.interface gtk-theme "Flat-Remix-GTK-Darker"

fi
