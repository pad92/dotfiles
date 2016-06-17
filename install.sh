#/usr/bin/env sh

BIN_DEPS='git sudo'

# === CHECKS ===
for BIN in $BIN_DEPS; do
    which $BIN 1>/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "Error: Required file could not be found: $BIN"
        exit 1
    fi
done


git clone --recursive http://git.depad.fr/pascal/dotfiles.git ~/.dotfiles

ln -s ~/.dotfiles/zshrc ~/.zshrc
ln -s ~/.dotfiles/screenrc ~/.screenrc
ln -s ~/.dotfiles/byobu ~/.byobu
if [ "$(id -u)" != "0" ]; then
	sudo apt-get install python python-newt
else
	apt-get install python python-newt
fi
ln -s ~/.dotfiles/vimrc ~/.vimrc
ln -s ~/.dotfiles/vim ~/.vim
vim +PluginInstall +qall
ln -s ~/.dotfiles/tmux.conf .tmux.conf

