-- Main Hyprland Lua Configuration (v0.55)

local config = require("config")

require("conf.monitors")
require("conf.autostart")
require("conf.input")
require("conf.appearance")
require("conf.animations")
require("conf.keybindings")
require("conf.windowrules")

local host = require("include.host")
local messages = host.load()

table.insert(messages, "Hyprland Lua configuration loaded successfully")

hl.notification.create({
  text = table.concat(messages, "\n"),
  duration = config.notifications.duration
})
