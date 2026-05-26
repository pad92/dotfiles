-- Main Hyprland Lua Configuration (v0.55)

-- Load global configuration
local config = require("config")

-- Load configuration modules
require("conf.monitors")
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
  local found_path = package.searchpath(host_module, package.path)
  
  if found_path then
    local status, err = pcall(require, host_module)
    if status then
      table.insert(messages, "Host config loaded: " .. hostname)
    else
      print("Error loading host configuration: " .. tostring(err))
    end
  else
    -- Fallback to default host-specific configuration
    local default_module = "hosts.default"
    local default_found = package.searchpath(default_module, package.path)
    
    if default_found then
      local status, err = pcall(require, default_module)
      if status then
        table.insert(messages, "Default host config loaded")
      else
        print("Error loading default host configuration: " .. tostring(err))
      end
    else
      print("No host-specific or default configuration found")
    end
  end
end

table.insert(messages, "Hyprland Lua configuration loaded successfully")

hl.notification.create({
  text = table.concat(messages, "\n"),
  duration = config.notifications.duration
})
