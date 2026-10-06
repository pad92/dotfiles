local hl = rawget(_G, "hl")

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
local messages, host_config_loaded = host.load()

local load_status = host_config_loaded and "loaded successfully" or "loaded with errors"
table.insert(messages, "Hyprland Lua configuration " .. load_status)

hl.notification.create({
  text = table.concat(messages, "\n"),
  duration = config.notifications.duration,
})
