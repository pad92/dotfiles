return {
  -- [ CONFIGURATION DU SERVEUR DE LANGAGE (LSP) ]
  {
    "neovim/nvim-lspconfig",
    dependencies = {
      "williamboman/mason.nvim",
      "williamboman/mason-lspconfig.nvim",
      "hrsh7th/cmp-nvim-lsp", -- Capacités de complétion
    },
    config = function()
      require("mason").setup()
      require("mason-lspconfig").setup({
        ensure_installed = { "lua_ls" }
      })

      -- Appliquer les capabilities de complétion globales
      vim.lsp.config("*", {
        capabilities = require("cmp_nvim_lsp").default_capabilities()
      })

      -- Configuration native moderne Neovim 0.11+
      vim.lsp.config.lua_ls = {
        settings = {
          Lua = {
            diagnostics = { globals = { "vim" } },
            telemetry = { enable = false },
          },
        },
      }

      -- Activer le serveur Lua
      vim.lsp.enable("lua_ls")
    end,
  },
}
