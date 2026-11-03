local vim = rawget(_G, "vim")

local indent_blankline_tag
local lualine_tag
if vim.fn.has("nvim-0.8") == 0 then
  indent_blankline_tag = "v2.20.8"
  lualine_tag = "compat-nvim-0.6"
elseif vim.fn.has("nvim-0.12") == 0 then
  indent_blankline_tag = "v3.6.0"
end

return {
  -- [ MODERNIZED GRUVBOX THEME ]
  {
    "ellisonleao/gruvbox.nvim",
    priority = 1000, -- Load the theme first
    config = function()
      require("gruvbox").setup({
        contrast = "hard",
        palette_overrides = {
          dark0_hard = "#1d2021",
        },
      })
      vim.cmd("colorscheme gruvbox")
    end,
  },

  -- [ STATUS LINE (Lualine) ]
  {
    "nvim-lualine/lualine.nvim",
    tag = lualine_tag,
    dependencies = { "nvim-tree/nvim-web-devicons" },
    config = function()
      require("lualine").setup({
        options = {
          theme = "gruvbox",
          component_separators = { left = "│", right = "│" },
          section_separators = { left = "", right = "" },
        },
      })
    end,
  },

  -- [ VERTICAL INDENTATION GUIDES ]
  {
    "lukas-reineke/indent-blankline.nvim",
    tag = indent_blankline_tag,
    main = vim.fn.has("nvim-0.8") == 1 and "ibl" or "indent_blankline",
    config = function()
      if vim.fn.has("nvim-0.8") == 1 then
        require("ibl").setup({
          indent = { char = "│" },
          scope = { enabled = false },
        })
      else
        require("indent_blankline").setup({
          char = "│",
          show_current_context = false,
        })
      end
    end,
  },

  -- [ CSS/HEX COLOR HIGHLIGHTER ]
  {
    "NvChad/nvim-colorizer.lua",
    config = function()
      require("colorizer").setup()
    end,
  },
}
