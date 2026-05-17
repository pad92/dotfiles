-- Main Hyprland Lua Configuration (v0.55)

-- Load global configuration
local config = require("config")

-- Load configuration modules
require("conf.monitors")
require("conf.environment")
require("conf.autostart")
require("conf.input")
require("conf.layout")
require("conf.appearance")
require("conf.animations")
require("conf.keybindings")
require("conf.windowrules")
require("conf.workspaces")

-- Host specific configuration
-- Optimized: Load host-specific config dynamically without symlinks
local hostname = os.getenv("HOSTNAME")
if not hostname then
  -- Fallback to shell if environment variable is not set
  local handle = io.popen("hostname")
  hostname = handle:read("*a"):gsub("%s+", "")
  handle:close()
end

local messages = {}
if hostname then
  local host_module = "hosts." .. hostname
  local status, err = pcall(require, host_module)
  if status then
    table.insert(messages, "Host config loaded: " .. hostname)
  else
    print("Host-specific configuration not found for: " .. hostname)
  end
end

table.insert(messages, "Hyprland Lua configuration loaded successfully")

hl.notification.create({
  text = table.concat(messages, "\n"),
  duration = config.notif_duration
})
