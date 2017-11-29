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
        sudo dnf install newt
    else
        dnf newt
    fi
fi
vim +PluginInstall +qall

sudo dnf copr enable tcg/themes && sudo dnf install materia-theme

if which gsettings 1>/dev/null 2>&1 ; then 
    gsettings set org.gnome.shell.extensions.user-theme name "Flat Remix"
    gsettings set org.gnome.desktop.interface icon-theme "Flat Remix"
    gsettings set org.gnome.desktop.interface gtk-theme "Materia-compact"
    gsettings set org.gnome.desktop.wm.preferences workspace-names "['WS1', 'WS2', 'WS3', 'WS4']"
fi
