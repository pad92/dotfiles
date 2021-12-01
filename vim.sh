#!/bin/sh

[ -e ~/.vim ] && echo '~/.vim exist' && exit 1
[ -e ~/.vimrc ] && echo '~/.vimrc exist' && exit 1

TMP_VIM=$(mktemp -u /tmp/vimrc.XXXXXX)
git clone --recursive https://gitlab.com/pad92/dotfiles.git "${TMP_VIM}"
mv "${TMP_VIM}/.vim" ~/
mv "${TMP_VIM}/.vimrc" ~/
rm -fr "${TMP_VIM}/"
vim +BundleInstall! +BundleClean +q
