" Vundle is cloned by the dotfiles role or scripts/vim.sh. Without it, Vim
" starts without plugins.
if filereadable(expand('~/.vim/bundle/Vundle.vim/autoload/vundle.vim'))
  filetype off    " required by vundle

  " set the runtime path to include Vundle and initialize
  set rtp+=~/.vim/bundle/Vundle.vim
  call vundle#begin()

  " let Vundle manage Vundle, required
  Plugin 'morhetz/gruvbox'
  Plugin 'VundleVim/Vundle.vim'
  Plugin 'airblade/vim-gitgutter'
  Plugin 'tpope/vim-fugitive'
  Plugin 'suan/vim-instant-markdown', {'rtp': 'after'}
  Plugin 'chrisbra/colorizer'
  Plugin 'editorconfig/editorconfig-vim'

  " All of your Plugins must be added before the following line
  call vundle#end()            " required
endif
filetype plugin indent on    " required
