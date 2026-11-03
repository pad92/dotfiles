local vim = rawget(_G, "vim")

-- ========================================================================== --
--                    LAZY.NVIM BOOTSTRAP (lazy.lua)                          --
-- ========================================================================== --

if vim.fn.has("nvim-0.8") == 0 then
  require("config.legacy_plugins").setup()
  return
end

local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
local uv = vim.uv or vim.loop
if not uv.fs_stat(lazypath) then
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

-- Load every plugin spec from the 'lua/plugins/' directory
require("lazy").setup({
  spec = {
    { import = "plugins" },
  },
  install = { colorscheme = { "gruvbox" } },
  checker = { enabled = false }, -- Disable slow automatic update checks at startup
})
