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
    sudo apt-get install python python-newt screenfetch
  else
    apt-get install python python-newt screenfetch
  fi
else
  if [ "$(id -u)" != "0" ]; then
    sudo dnf copr enable tcg/themes
    sudo dnf copr enable daniruiz/flat-remix
    sudo dnf install newt tilix-nautilus tilix numix-icon-theme-circle materia-theme screenfetch
  else
    dnf copr enable tcg/themes
    dnf copr enable daniruiz/flat-remix
    dnf newt tilix-nautilus tilix numix-icon-theme-circle materia-theme screenfetch
  fi
fi
vim +PluginInstall +qall

dconf load /com/gexperts/Tilix/ < tilix.dconf

if which gsettings 1>/dev/null 2>&1 ; then
  gsettings set org.gnome.shell.extensions.user-theme name "Flat-Remix";
  gsettings set org.gnome.desktop.interface icon-theme "Numix"
  gsettings set org.gnome.desktop.interface gtk-theme "Materia-compact"
fi
