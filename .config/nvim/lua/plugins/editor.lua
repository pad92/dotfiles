return {
  -- [ TELESCOPE (Fuzzy Finder) ]
  {
    "nvim-telescope/telescope.nvim",
    branch = "0.1.x",
    cmd = "Telescope", -- Loaded on demand (keymaps call :Telescope)
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

  -- [ GITSIGNS (Fast Git integration) ]
  {
    "lewis6991/gitsigns.nvim",
    event = "VeryLazy",
    config = function()
      require("gitsigns").setup({
        signs = {
          add = { text = "│" },
          change = { text = "│" },
          delete = { text = "_" },
          topdelete = { text = "‾" },
          changedelete = { text = "~" },
        },
        current_line_blame = false, -- Inline blame off by default (toggle with <leader>gb)
        on_attach = function(bufnr)
          local gs = require("gitsigns")
          local map = function(mode, keys, fn, desc)
            vim.keymap.set(mode, keys, fn, { buffer = bufnr, desc = "Git : " .. desc })
          end

          -- Hunk navigation (respects diff mode)
          map("n", "]c", function()
            if vim.wo.diff then
              vim.cmd.normal({ "]c", bang = true })
            else
              gs.nav_hunk("next")
            end
          end, "Hunk suivant")
          map("n", "[c", function()
            if vim.wo.diff then
              vim.cmd.normal({ "[c", bang = true })
            else
              gs.nav_hunk("prev")
            end
          end, "Hunk précédent")

          -- Hunk actions
          map({ "n", "v" }, "<leader>gs", gs.stage_hunk, "Stage le hunk")
          map({ "n", "v" }, "<leader>gr", gs.reset_hunk, "Reset le hunk")
          map("n", "<leader>gp", gs.preview_hunk, "Aperçu du hunk")
          map("n", "<leader>gb", gs.toggle_current_line_blame, "Basculer le blame de ligne")
          map("n", "<leader>gd", gs.diffthis, "Diff du tampon")
        end,
      })
    end,
  },

  -- [ AUTOPAIRS (Bracket auto-closing) ]
  {
    "windwp/nvim-autopairs",
    event = "InsertEnter",
    config = true,
  },
}
