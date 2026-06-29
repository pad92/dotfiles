-- ========================================================================== --
--                     KEYBINDINGS (keymaps.lua)                              --
-- ========================================================================== --

local key = vim.keymap.set

-- Leader key definition (Space)
vim.g.mapleader = " "
vim.g.maplocalleader = " "

-- Faster split navigation (Ctrl-h/j/k/l)
key("n", "<C-h>", "<C-w>h", { desc = "Aller au split de gauche" })
key("n", "<C-j>", "<C-w>j", { desc = "Aller au split du bas" })
key("n", "<C-k>", "<C-w>k", { desc = "Aller au split du haut" })
key("n", "<C-l>", "<C-w>l", { desc = "Aller au split de droite" })

-- Esc clears the current search highlight
key("n", "<Esc>", "<cmd>nohlsearch<CR>", { desc = "Effacer la surbrillance de recherche" })

-- Telescope shortcuts (loaded on demand via `cmd = "Telescope"`)
key("n", "<leader>ff", "<cmd>Telescope find_files<CR>", { desc = "Rechercher des fichiers" })
key("n", "<leader>fg", "<cmd>Telescope live_grep<CR>", { desc = "Rechercher du texte (Grep)" })
key("n", "<leader>fb", "<cmd>Telescope buffers<CR>", { desc = "Lister les buffers ouverts" })
key("n", "<leader>fh", "<cmd>Telescope help_tags<CR>", { desc = "Rechercher dans l'aide" })

-- Legacy shortcut to toggle line numbers (double Ctrl-N)
key(
  "n",
  "<C-n><C-n>",
  ":set invnumber invrelativenumber<CR>",
  { silent = true, desc = "Activer/désactiver les numéros de ligne" }
)
