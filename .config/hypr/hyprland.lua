-- Main Hyprland Lua Configuration (v0.55)

-- Load configuration modules
require("conf.variables")
require("conf.monitor")
require("conf.environment")
require("conf.autostart")
require("conf.input")
require("conf.layout")
require("conf.misc")
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
  if not status then
    print("Host-specific configuration not found for: " .. hostname)
  end
end
