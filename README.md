Fork of github.com:DisasteR

# dotfiles
     git clone --recursive http://git.depad.fr/pascal/dotfiles.git ~/.dotfiles

## Zsh
     ln -sf ~/.dotfiles/zshrc ~/.zshrc

## Screen
     ln -sf ~/.dotfiles/screenrc ~/.screenrc
     ln -sf ~/.dotfiles/byobu ~/.byobu
     apt-get install python python-newt

## Vim
     ln -sf ~/.dotfiles/vimrc ~/.vimrc
     ln -sf ~/.dotfiles/vim ~/.vim
     vim +PluginInstall +qall

## Tmux
     ln -sf ~/.dotfiles/tmux.conf ~/.tmux.conf

## Terminator
     ln -sf ~/.dotfiles/terminator ~/.config/terminator

## Tint2
     ln -sf ~/.dotfiles/tint2 ~/.config/tint2

# Fonts
     ln -sf -s ~/.dotfiles/fonts ~/.fonts

# Gnome
## Theme
     ln -sf ~/.dotfiles/themes ~/.themes
     gsettings set org.gnome.shell.extensions.user-theme name "Flat Remix"

## Icons
     ln -sf ~/.dotfiles/icons ~/.icons
     gsettings set org.gnome.desktop.interface icon-theme "Flat Remix"

## GTK

https://github.com/nana-4/Flat-Plat
