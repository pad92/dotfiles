" Gruvbox options
" see https://github.com/morhetz/gruvbox
set background=dark    " Setting dark mode
let g:gruvbox_contrast_dark='hard'
let g:gruvbox_number_column='blue'
let g:gruvbox_imporeved_strings=1
colorscheme gruvbox

" Vim5 and later versions support syntax highlighting. Uncommenting the next
" line enables syntax highlighting by default.
if has("syntax")
  syntax on
endif

""" statusline
" cf the default statusline: %<%f\ %h%m%r%=%-14.(%l,%c%V%)\ %P
set statusline=%<\ %n:%f\ %m%r%y%=%-35.(line:\ %l\ of\ %L,\ col:\ %c%V\ (%P)%)

highlight Folded ctermfg=DarkGreen ctermbg=Black

:highlight LineNr term=bold cterm=NONE ctermfg=DarkGrey ctermbg=Black gui=NONE guifg=DarkGrey guibg=Black
