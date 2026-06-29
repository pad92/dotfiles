-- ========================================================================== --
--                  GLOBAL SETTINGS & OPTIONS (options.lua)                    --
-- ========================================================================== --

local opt = vim.opt

-- Display & visual aids
opt.number = true -- Show line numbers
opt.relativenumber = true -- Relative line numbers
opt.signcolumn = "yes" -- Keep the sign column always open
opt.termguicolors = true -- True color (modern 24-bit colors)
opt.cursorline = true -- Highlight the current line

-- Search
opt.ignorecase = true -- Case-insensitive by default
opt.smartcase = true -- Case-sensitive when an uppercase letter is typed
opt.incsearch = true -- Incremental search while typing
opt.hlsearch = true -- Highlight search matches

-- Indentation & tabs
opt.tabstop = 4 -- Width of a tab
opt.shiftwidth = 4 -- Indentation width
opt.expandtab = true -- Expand tabs into spaces
opt.smartindent = true -- Smart auto-indentation

-- Behavior & system
opt.mouse = "a" -- Enable the mouse in all modes
opt.clipboard = "unnamedplus" -- Sync with the system clipboard
opt.swapfile = false -- Disable legacy swap files
opt.undofile = true -- Persistent undo history
opt.updatetime = 250 -- Faster refresh (for Git / LSP)
opt.timeoutlen = 300 -- Timeout for mapped key sequences
opt.scrolloff = 8 -- Keep 8 lines visible above/below the cursor

-- Window layout
opt.splitright = true -- Vertical splits open on the right
opt.splitbelow = true -- Horizontal splits open below

-- Invisible characters
opt.list = true
opt.listchars = { tab = "» ", trail = "·", nbsp = "␣" }

-- Folding: foldmethod/foldexpr (Treesitter) are set per filetype in
-- plugins/treesitter.lua (where a parser is started); here we only keep the
-- global behavior: do not open a file with folds closed.
opt.foldenable = false

-- Netrw (built-in file explorer) configuration
vim.g.netrw_banner = 0
vim.g.netrw_liststyle = 3
vim.g.netrw_winsize = 25

-- ========================================================================== --
-- BACKUP DIRECTORIES                                                          --
-- ========================================================================== --
local state_dir = vim.fn.stdpath("state")
local backup_dir = state_dir .. "/backup"

if vim.fn.isdirectory(backup_dir) == 0 then
  vim.fn.mkdir(backup_dir, "p")
end

opt.backup = true
opt.writebackup = true
opt.backupskip = "/tmp/*"
opt.backupext = ".bak"
opt.backupdir = backup_dir

-- ========================================================================== --
-- AUTOCOMMANDS & SPECIFIC BEHAVIORS                                          --
-- ========================================================================== --
-- Automatically restore the last cursor position
vim.api.nvim_create_autocmd("BufReadPost", {
  callback = function()
    local mark = vim.api.nvim_buf_get_mark(0, '"')
    local lcount = vim.api.nvim_buf_line_count(0)
    if mark[1] > 0 and mark[1] <= lcount then
      pcall(vim.api.nvim_win_set_cursor, 0, mark)
    end
  end,
})
