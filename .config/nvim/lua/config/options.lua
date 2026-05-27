-- ========================================================================== --
--                  PARAMÈTRES ET OPTIONS GLOBALES (options.lua)               --
-- ========================================================================== --

local opt = vim.opt

-- Affichage & Rapprochement visuel
opt.number = true               -- Affiche les numéros de ligne
opt.relativenumber = true       -- Numéros de ligne relatifs
opt.signcolumn = "yes"          -- Laisse la colonne de gauche ouverte
opt.termguicolors = true        -- True Colors (couleurs 24-bits modernes)
opt.cursorline = true           -- Met en surbrillance la ligne courante

-- Recherche
opt.ignorecase = true           -- Insensible à la casse par défaut
opt.smartcase = true            -- Sensible à la casse si on tape une majuscule
opt.incsearch = true            -- Recherche dynamique en cours de frappe
opt.hlsearch = true             -- Surligne les résultats de recherche

-- Indentation & Tabulations
opt.tabstop = 4                 -- Largeur d'une tabulation
opt.shiftwidth = 4              -- Largeur de l'indentation
opt.expandtab = true            -- Convertit les tabulations en espaces
opt.smartindent = true          -- Indentation intelligente

-- Comportement & Système
opt.mouse = "a"                 -- Active pleinement la souris
opt.clipboard = "unnamedplus"   -- Synchronise le presse-papiers système
opt.swapfile = false            -- Désactive les fichiers swap obsolètes
opt.backup = true               -- Conserve les backups
opt.writebackup = true
opt.undofile = true             -- Historique persistant des modifications
opt.updatetime = 250            -- Rafraîchissement plus rapide (pour Git / LSP)
opt.timeoutlen = 300            -- Temps de réponse aux touches combinées
opt.scrolloff = 8               -- Conserve toujours 8 lignes de visibilité sous/sur le curseur

-- Disposition des fenêtres
opt.splitright = true           -- Les splits verticaux s'ouvrent à droite
opt.splitbelow = true           -- Les splits horizontaux s'ouvrent en bas

-- Caractères invisibles
opt.list = true
opt.listchars = { tab = "» ", trail = "·", nbsp = "␣" }

-- Pliage (Folding) moderne via Treesitter
opt.foldmethod = "expr"
opt.foldexpr = "v:lua.vim.treesitter.foldexpr()"
opt.foldenable = false          -- N'ouvre pas le fichier avec les plis fermés par défaut

-- Configuration Netrw (explorateur natif)
vim.g.netrw_banner = 0
vim.g.netrw_liststyle = 3
vim.g.netrw_winsize = 25

-- ========================================================================== --
-- REPERTOIRES DE SAUVEGARDE & BACKUP                                         --
-- ========================================================================== --
local state_dir = vim.fn.stdpath("state")
local backup_dir = state_dir .. "/backup"
local swap_dir = state_dir .. "/swap"

-- Crée automatiquement les répertoires s'ils n'existent pas
for _, dir in ipairs({ backup_dir, swap_dir }) do
  if vim.fn.isdirectory(dir) == 0 then
    vim.fn.mkdir(dir, "p")
  end
end

opt.backup = true
opt.backupskip = "/tmp/*"
opt.backupext = ".bak"
opt.directory = swap_dir
opt.backupdir = backup_dir
opt.writebackup = true

-- ========================================================================== --
-- AUTOMATIONS & COMPORTEMENTS SPÉCIFIQUES                                    --
-- ========================================================================== --
-- Restauration automatique de la position du curseur
vim.api.nvim_create_autocmd("BufReadPost", {
  callback = function()
    local mark = vim.api.nvim_buf_get_mark(0, '"')
    local lcount = vim.api.nvim_buf_line_count(0)
    if mark[1] > 0 and mark[1] <= lcount then
      pcall(vim.api.nvim_win_set_cursor, 0, mark)
    end
  end,
})
