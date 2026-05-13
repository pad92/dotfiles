-- Main Hyprland Lua Configuration (v0.55)

-- Load global configuration
local config = require("config")

-- Load configuration modules
require("conf.monitor")
require("conf.environment")
require("conf.autostart")
require("conf.input")
require("conf.layout")
require("conf.appearance")
require("conf.animations")
require("conf.keybindings")
require("conf.windowrules")

require("workspaces")

-- Host specific configuration
-- Optimized: Load host-specific config dynamically without symlinks
local hostname = os.getenv("HOSTNAME")
if not hostname then
  -- Fallback to shell if environment variable is not set
  local handle = io.popen("hostname")
  hostname = handle:read("*a"):gsub("%s+", "")
  handle:close()
end

if hostname then
  local host_module = "hosts." .. hostname
  local status, err = pcall(require, host_module)
  if status then
    hl.notification.create({
      text = "Host config loaded: " .. hostname,
      duration = config.notif_duration
    })
  else
    print("Host-specific configuration not found for: " .. hostname)
  end
end

hl.notification.create({
  text = "Hyprland Lua configuration loaded successfully",
  duration = config.notif_duration
})
