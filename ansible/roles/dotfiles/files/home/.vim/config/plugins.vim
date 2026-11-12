" The plugins are a Vim package in ~/.vim/pack/dotfiles/start, which Vim
" loads after this file (:help packages). The dotfiles role clones them at the
" commits pinned in dotfiles_vim_pack_plugins, and the vim.tar.gz archive
" ships the same ones. Without them, Vim starts without plugins.

" vim-instant-markdown previews each Markdown buffer through the Node.js
" instant-markdown-d server, which reports an error when it is not installed.
" Start the preview by hand with :InstantMarkdownPreview.
let g:instant_markdown_autostart = 0

filetype plugin indent on
