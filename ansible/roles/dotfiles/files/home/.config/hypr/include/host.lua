-- Applies the host settings that Ansible renders into hosts/settings.lua from
-- the dotfiles_hypr_* variables. The deployment has already resolved the
-- machine's monitors and rules, so nothing here depends on the hostname.
local hl = rawget(_G, "hl")

local M = {}

local function apply(settings)
  for _, monitor in ipairs(settings.monitors or {}) do
    hl.monitor(monitor)
  end
  for _, rule in ipairs(settings.workspace_rules or {}) do
    hl.workspace_rule(rule)
  end
  for _, rule in ipairs(settings.window_rules or {}) do
    hl.window_rule(rule)
  end
  if next(settings.config or {}) then
    hl.config(settings.config)
  end
end

function M.load()
  local messages = {}

  local loaded, settings = pcall(require, "hosts.settings")
  if not loaded then
    table.insert(messages, "Host settings failed: " .. tostring(settings))
    return messages, false
  end

  local applied, err = pcall(apply, settings)
  if not applied then
    table.insert(messages, "Host settings failed: " .. tostring(err))
    return messages, false
  end

  table.insert(messages, "Host settings loaded")
  return messages, true
end

return M
