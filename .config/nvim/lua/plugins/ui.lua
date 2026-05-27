return {
  -- [ THÈME GRUVBOX MODERNISÉ ]
  {
    "ellisonleao/gruvbox.nvim",
    priority = 1000, -- Charge le thème en premier
    config = function()
      require("gruvbox").setup({
        contrast = "hard",
        palette_overrides = {
          dark0_hard = "#1d2021",
        }
      })
      vim.cmd("colorscheme gruvbox")
    end,
  },

  -- [ BARRE DE STATUT (Lualine) ]
  {
    "nvim-lualine/lualine.nvim",
    dependencies = { "nvim-tree/nvim-web-devicons" },
    config = function()
      require("lualine").setup({
        options = {
          theme = "gruvbox",
          component_separators = { left = "│", right = "│" },
          section_separators = { left = "", right = "" },
        }
      })
    end,
  },

  -- [ GUIDES VERTICAUX D'INDENTATION ]
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

  -- [ COLORISEUR DE CODES CSS/HEX ]
  {
    "NvChad/nvim-colorizer.lua",
    config = function()
      require("colorizer").setup()
    end,
  },
}
