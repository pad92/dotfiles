local vim = rawget(_G, "vim")

local treesitter_tag
if vim.fn.has("nvim-0.8") == 0 then
  treesitter_tag = "v0.8.5"
elseif vim.fn.has("nvim-0.12") == 0 then
  treesitter_tag = "v0.9.2"
end

return {
  -- [ TREESITTER (AST syntax highlighting) ]
  {
    "nvim-treesitter/nvim-treesitter",
    branch = vim.fn.has("nvim-0.12") == 1 and "main" or nil,
    tag = treesitter_tag,
    lazy = false,
    build = ":TSUpdate",
    config = function()
      -- Parsers to install (markdown_inline = injections inside markdown)
      local parsers = {
        "lua",
        "vim",
        "vimdoc",
        "markdown",
        "markdown_inline",
        "javascript",
        "typescript",
        "html",
        "css",
        "bash",
      }

      local treesitter = require("nvim-treesitter")
      if type(treesitter.install) == "function" then
        -- nvim-treesitter main branch API (Neovim >= 0.12)
        treesitter.setup()
        treesitter.install(parsers)
      else
        -- Older nvim-treesitter checkouts expose parser installation through
        -- the configs module instead of nvim-treesitter.install().
        require("nvim-treesitter.configs").setup({
          ensure_installed = parsers,
          highlight = { enable = true },
          indent = { enable = true },
        })
      end

      if vim.fn.has("nvim-0.9") == 0 then
        return
      end

      -- Enable highlight + indent + folding for filetypes with an installed parser
      vim.api.nvim_create_autocmd("FileType", {
        pattern = {
          "lua",
          "vim",
          "help",
          "markdown",
          "javascript",
          "typescript",
          "html",
          "css",
          "sh",
          "bash",
        },
        callback = function()
          pcall(vim.treesitter.start)
          vim.bo.indentexpr = "v:lua.require'nvim-treesitter'.indentexpr()"
          vim.wo[0][0].foldmethod = "expr"
          vim.wo[0][0].foldexpr = "v:lua.vim.treesitter.foldexpr()"
        end,
      })
    end,
  },
}
