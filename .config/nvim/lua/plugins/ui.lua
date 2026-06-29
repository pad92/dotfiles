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
    main = "ibl",
    config = function()
      require("ibl").setup({
        indent = { char = "│" },
        scope = { enabled = false },
      })
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
