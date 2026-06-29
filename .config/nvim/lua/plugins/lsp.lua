return {
  -- [ LANGUAGE SERVER (LSP) CONFIGURATION ]
  {
    "neovim/nvim-lspconfig",
    dependencies = {
      "mason-org/mason.nvim",
      "mason-org/mason-lspconfig.nvim",
      "hrsh7th/cmp-nvim-lsp", -- Completion capabilities
    },
    config = function()
      require("mason").setup()
      require("mason-lspconfig").setup({
        ensure_installed = { "lua_ls" },
        -- automatic_enable = true (default): mason-lspconfig calls vim.lsp.enable
        -- for every installed server, so there is no need to do it manually.
      })

      -- Apply global completion capabilities
      vim.lsp.config("*", {
        capabilities = require("cmp_nvim_lsp").default_capabilities(),
      })

      -- Modern native configuration (Neovim 0.11+)
      vim.lsp.config.lua_ls = {
        settings = {
          Lua = {
            diagnostics = { globals = { "vim" } },
            telemetry = { enable = false },
          },
        },
      }

      -- LSP keymaps, set buffer-local when a server attaches.
      -- Neovim 0.11 already provides grn (rename), gra (code action), grr
      -- (references), gri (implementation), gO (symbols) and K (hover); fill the rest.
      vim.api.nvim_create_autocmd("LspAttach", {
        callback = function(event)
          local map = function(keys, fn, desc)
            vim.keymap.set("n", keys, fn, { buffer = event.buf, desc = "LSP : " .. desc })
          end
          map("gd", vim.lsp.buf.definition, "Aller à la définition")
          map("gD", vim.lsp.buf.declaration, "Aller à la déclaration")
          map("gi", vim.lsp.buf.implementation, "Aller à l'implémentation")
          map("<leader>e", vim.diagnostic.open_float, "Diagnostic sous le curseur")
          map("<leader>lf", function()
            vim.lsp.buf.format({ async = true })
          end, "Formater le tampon")
        end,
      })
    end,
  },
}
