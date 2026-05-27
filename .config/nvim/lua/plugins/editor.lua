return {
  -- [ TELESCOPE (Fuzzy Finder) ]
  {
    "nvim-telescope/telescope.nvim",
    branch = "0.1.x",
    dependencies = { "nvim-lua/plenary.nvim" },
    config = function()
      require("telescope").setup({
        defaults = {
          mappings = {
            i = {
              ["<C-u>"] = false,
              ["<C-d>"] = false,
            },
          },
        },
      })
    end,
  },

  -- [ GITSIGNS (Intégration Git rapide) ]
  {
    "lewis6991/gitsigns.nvim",
    config = function()
      require("gitsigns").setup({
        signs = {
          add          = { text = "│" },
          change       = { text = "│" },
          delete       = { text = "_" },
          topdelete    = { text = "‾" },
          changedelete = { text = "~" },
        },
        current_line_blame = true, -- Affiche l'auteur du commit en filigrane
      })
    end,
  },

  -- [ AUTOPAIRS (Fermeture de parenthèses) ]
  {
    "windwp/nvim-autopairs",
    event = "InsertEnter",
    config = true,
  },
}
