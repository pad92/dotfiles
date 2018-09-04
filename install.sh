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

DOTFILES='.zshrc .screenrc .byobu .vimrc .vim .tmux.conf .tmux .fonts .themes .icons'
for DOTFILE in $DOTFILES; do
  if [ ! -L ~/$DOTFILE ]; then
    ln -s ~/.dotfiles/$DOTFILE ~/$DOTFILE
  fi
done

CONFFILES='terminator tint2'
for CONFFILE in $CONFFILES; do
  if [ ! -L ~/.config/$CONFFILE ]; then
    if [ ! -d ~/.config/$CONFFILE ]; then
      mkdir ~/.config/$CONFFILE
    fi
    ln -s ~/.dotfiles/$CONFFILE ~/.config/$CONFFILE
  fi
done

if which apt-get 1>/dev/null 2>&1 ; then
  if [ "$(id -u)" != "0" ]; then
    sudo apt-get install python python-newt
  else
    apt-get install python python-newt
  fi
else
  if [ "$(id -u)" != "0" ]; then
    sudo dnf copr enable tcg/themes
    sudo dnf install newt tilix-nautilus tilix numix-icon-theme-circle materia-theme
  else
    dnf copr enable tcg/themes
    dnf newt tilix-nautilus tilix numix-icon-theme-circle materia-theme
  fi
fi
vim +PluginInstall +qall

dconf load /com/gexperts/Tilix/ < tilix.dconf

if which gsettings 1>/dev/null 2>&1 ; then
  gsettings set org.gnome.shell.extensions.user-theme name "Flat-Plat"
  gsettings set org.gnome.desktop.interface icon-theme "Numix"
  gsettings set org.gnome.desktop.interface gtk-theme "Materia-compact"
fi
