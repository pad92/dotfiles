-- ========================================================================== --
--                     RACCOURCIS CLAVIER (keymaps.lua)                       --
-- ========================================================================== --

local key = vim.keymap.set

-- Définition du raccourci Leader (Espace)
vim.g.mapleader = " "
vim.g.maplocalleader = " "

-- Navigation entre les splits plus rapide (Ctrl-h/j/k/l)
key("n", "<C-h>", "<C-w>h", { desc = "Aller au split de gauche" })
key("n", "<C-j>", "<C-w>j", { desc = "Aller au split du bas" })
key("n", "<C-k>", "<C-w>k", { desc = "Aller au split du haut" })
key("n", "<C-l>", "<C-w>l", { desc = "Aller au split de droite" })

-- Esc vide le surlignage de recherche courant
key("n", "<Esc>", "<cmd>nohlsearch<CR>", { desc = "Effacer la surbrillance de recherche" })

-- Raccourcis pour Telescope (Fuzzy Finding moderne - se charge à la demande)
key("n", "<leader>ff", "<cmd>Telescope find_files<CR>", { desc = "Rechercher des fichiers" })
key("n", "<leader>fg", "<cmd>Telescope live_grep<CR>", { desc = "Rechercher du texte (Grep)" })
key("n", "<leader>fb", "<cmd>Telescope buffers<CR>", { desc = "Lister les buffers ouverts" })
key("n", "<leader>fh", "<cmd>Telescope help_tags<CR>", { desc = "Rechercher dans l'aide" })

-- Raccourci historique pour les numéros de ligne (double Ctrl-N)
key("n", "<C-n><C-n>", ":set invnumber invrelativenumber<CR>", { silent = true, desc = "Activer/désactiver les numéros de ligne" })
