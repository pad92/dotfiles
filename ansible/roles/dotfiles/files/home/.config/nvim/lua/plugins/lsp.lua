local vim = rawget(_G, "vim")

local function tag_before(version, tag)
  if vim.fn.has("nvim-" .. version) == 0 then
    return tag
  end
end

local mason_tag = tag_before("0.10", "v1.8.0")
local mason_lspconfig_tag = tag_before("0.10", "v1.25.0")
local lspconfig_tag = tag_before("0.11", "v0.1.8")

return {
  -- [ LANGUAGE SERVER (LSP) CONFIGURATION ]
  {
    "neovim/nvim-lspconfig",
    tag = lspconfig_tag,
    dependencies = {
      { "mason-org/mason.nvim", tag = mason_tag },
      { "mason-org/mason-lspconfig.nvim", tag = mason_lspconfig_tag },
      "hrsh7th/cmp-nvim-lsp", -- Completion capabilities
    },
    config = function()
      require("mason").setup()
      require("mason-lspconfig").setup({
        ensure_installed = { "lua_ls" },
      })

      local capabilities = require("cmp_nvim_lsp").default_capabilities()
      local settings = {
        settings = {
          Lua = {
            diagnostics = { globals = { "vim" } },
            telemetry = { enable = false },
          },
        },
      }

      local function on_attach(_, bufnr)
        local map = function(keys, fn, desc)
          vim.keymap.set("n", keys, fn, { buffer = bufnr, desc = "LSP : " .. desc })
        end
        map("gd", vim.lsp.buf.definition, "Aller à la définition")
        map("gD", vim.lsp.buf.declaration, "Aller à la déclaration")
        map("gi", vim.lsp.buf.implementation, "Aller à l'implémentation")
        map("<leader>e", vim.diagnostic.open_float, "Diagnostic sous le curseur")
        map("<leader>lf", function()
          if vim.lsp.buf.format then
            vim.lsp.buf.format({ async = true })
          else
            vim.lsp.buf.formatting()
          end
        end, "Formater le tampon")
      end

      if vim.fn.has("nvim-0.11") == 1 then
        vim.lsp.config("*", {
          capabilities = capabilities,
          on_attach = on_attach,
        })
        vim.lsp.config.lua_ls = vim.tbl_extend("force", settings, {
          capabilities = capabilities,
          on_attach = on_attach,
        })
        vim.api.nvim_create_autocmd("LspAttach", {
          callback = function(event)
            on_attach(vim.lsp.get_client_by_id(event.data.client_id), event.buf)
          end,
        })
      else
        local lspconfig = require("lspconfig")
        lspconfig.lua_ls.setup(vim.tbl_extend("force", settings, {
          capabilities = capabilities,
          on_attach = on_attach,
        }))
      end
    end,
  },
}
