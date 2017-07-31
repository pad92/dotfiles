#/usr/bin/env sh

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
    if [ ! -L ~/.$DOTFILE ]; then
        ln -s ~/.dotfiles/$DOTFILE ~/$DOTFILE
    fi
done
if [ ! -L ~/.config/terminator ]; then
    if [ ! -d ~/.config/terminator ]; then
        mkdir ~/.config/terminator
    fi
    ln -s ~/.dotfiles/terminator ~/.config/terminator
fi

if which apt-get 1>/dev/null 2>&1 ; then 
    if [ "$(id -u)" != "0" ]; then
        sudo apt-get install python python-newt
    else
        apt-get install python python-newt
    fi
else
    if [ "$(id -u)" != "0" ]; then
        sudo dnf install newt
    else
        dnf newt
    fi
fi
vim +PluginInstall +qall

if which gsettings 1>/dev/null 2>&1 ; then 
    gsettings set org.gnome.shell.extensions.user-theme name "Flat Remix"
    gsettings set org.gnome.desktop.interface icon-theme "Flat Remix"
fi
