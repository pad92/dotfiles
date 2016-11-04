Fork of github.com:DisasteR

# dotfiles
git clone --recursive http://git.depad.fr/pascal/dotfiles.git ~/.dotfiles

## Zsh
ln -s ~/.dotfiles/zshrc ~/.zshrc

## Screen
ln -s ~/.dotfiles/screenrc ~/.screenrc

ln -s ~/.dotfiles/byobu ~/.byobu

apt-get install python python-newt

## Vim
ln -s ~/.dotfiles/vimrc ~/.vimrc

ln -s ~/.dotfiles/vim ~/.vim

vim +PluginInstall +qall

## Tmux
ln -s ~/.dotfiles/tmux.conf .tmux.conf

## Terminator
ln -s ~/.dotfiles/terminator ~/.config/terminator

# Fonts
ln -s -s ~/.dotfiles/fonts .fonts
