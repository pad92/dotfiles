-- ========================================================================== --
--                    AMORÇAGE DE LAZY.NVIM (lazy.lua)                        --
-- ========================================================================== --

local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.uv.fs_stat(lazypath) then
  vim.fn.system({
    "git",
    "clone",
    "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git",
    "--branch=stable",
    lazypath,
  })
end
vim.opt.rtp:prepend(lazypath)

-- Charge tous les plugins configurés dans le dossier 'lua/plugins/'
require("lazy").setup({
  spec = {
    { import = "plugins" },
  },
  install = { colorscheme = { "gruvbox" } },
  checker = { enabled = false }, -- Désactive les vérifications automatiques lentes au démarrage
})
