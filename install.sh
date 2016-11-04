#/usr/bin/env sh

# === INIT ===
if [ "$(id -u)" -eq "0" ]; then
    BIN_DEPS='git apt-get'
else
    BIN_DEPS="$BIN_DEPS sudo"
fi

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

DOTFILES='zshrc screenrc byobu vimrc vim tmux.conf'
for DOTFILE in $DOTFILES; do
    if [ ! -L ~/.$DOTFILE ]; then
        ln -s ~/.dotfiles/$DOTFILE ~/.$DOTFILE
    fi
done
if [ ! -L ~/.config/terminator ]; then
    ln -s ~/.dotfiles/terminator ~/.config/terminator
    fi

if [ "$(id -u)" != "0" ]; then
	sudo apt-get install python python-newt
else
	apt-get install python python-newt
fi
vim +PluginInstall +qall
