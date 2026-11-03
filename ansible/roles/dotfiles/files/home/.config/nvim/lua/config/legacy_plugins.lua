local vim = rawget(_G, "vim")

local M = {}

local plugin_modules = {
  "plugins.ui",
  "plugins.editor",
  "plugins.cmp",
  "plugins.lsp",
  "plugins.treesitter",
}

-- These releases retain support for Neovim 0.7, whose APIs predate the current
-- plugin branches and lazy.nvim.
local legacy_refs = {
  ["gitsigns.nvim"] = "v0.6",
  ["indent-blankline.nvim"] = "v2.20.8",
  ["lualine.nvim"] = "compat-nvim-0.6",
  ["mason-lspconfig.nvim"] = "v1.25.0",
  ["mason.nvim"] = "v1.8.0",
  ["nvim-lspconfig"] = "v0.1.8",
  ["nvim-treesitter"] = "v0.8.5",
  ["telescope.nvim"] = "0.1.5",
  ["nvim-colorizer.lua"] = "0.10.0",
}

local function collect_specs()
  local specs = {}
  local seen = {}

  local function add(spec)
    if type(spec) == "string" then
      spec = { spec }
    end

    local repository = spec[1]
    if not repository or seen[repository] then
      return
    end
    seen[repository] = true

    for _, dependency in ipairs(spec.dependencies or {}) do
      add(dependency)
    end
    table.insert(specs, spec)
  end

  for _, module in ipairs(plugin_modules) do
    for _, spec in ipairs(require(module)) do
      add(spec)
    end
  end

  return specs
end

local function install_plugin(spec, root)
  local repository = spec[1]
  local name = repository:match("([^/]+)$")
  local path = root .. "/" .. name
  if vim.fn.isdirectory(path) == 1 then
    return name, path
  end

  local command = { "git", "clone", "--depth", "1" }
  local ref = legacy_refs[name] or spec.tag or spec.branch
  if ref then
    table.insert(command, "--branch")
    table.insert(command, ref)
  end
  table.insert(command, "https://github.com/" .. repository .. ".git")
  table.insert(command, path)

  local output = vim.fn.system(command)
  if vim.v.shell_error ~= 0 then
    error("Failed to install " .. repository .. ":\n" .. output)
  end

  return name, path
end

local function configure(spec)
  if type(spec.config) == "function" then
    spec.config()
  elseif spec.config == true then
    local module = spec.main or spec[1]:match("([^/]+)$")
    require(module).setup()
  end
end

function M.setup()
  local root = vim.fn.stdpath("data") .. "/site/pack/dotfiles/start"
  vim.fn.mkdir(root, "p")

  local specs = collect_specs()
  local installed = {}
  for _, spec in ipairs(specs) do
    local name, path = install_plugin(spec, root)
    table.insert(installed, { name = name, path = path })
    vim.opt.rtp:prepend(path)
  end

  for _, plugin in ipairs(installed) do
    vim.cmd("packadd " .. plugin.name)
  end

  for _, module in ipairs(plugin_modules) do
    for _, spec in ipairs(require(module)) do
      configure(spec)
    end
  end
end

return M
