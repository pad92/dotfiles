# dotfiles

git clone --recursive git@github.com:DisasteR/dotfiles.git ~/.dotfiles

## Zsh
ln -s ~/.dotfiles/zshrc ~/.zshrc

## Screen
ln -s ~/.dotfiles/screenrc ~/.screenrc

ln -s ~/.dotfiles/byobu ~/.byobu      

## Vim
ln -s ~/.dotfiles/vimrc ~/.vimrc

ln -s ~/.dotfiles/vim ~/.vim

vim +PluginInstall +qall
