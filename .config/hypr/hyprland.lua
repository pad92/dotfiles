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
local host = require("include.host")
local messages = host.load()

table.insert(messages, "Hyprland Lua configuration loaded successfully")

hl.notification.create({
  text = table.concat(messages, "\n"),
  duration = config.notifications.duration
})
