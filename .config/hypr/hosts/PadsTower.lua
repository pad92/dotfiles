local hl = rawget(_G, "hl")
local common = require("hosts.common")

local monitors = {
  common.asus_monitor("2560x1440@144"),
}

hl.monitor(common.dell_monitor)
for _, monitor in ipairs(monitors) do
  hl.monitor(monitor)
end

-- Route Steam/games to the ASUS monitor
local asus = common.asus_output
hl.window_rule({ match = { class = "^(?i)(steam)$", title = "^(?i)(Steam Big Picture Mode)$" }, monitor = asus })
hl.window_rule({ match = { class = "^(?i)(gamescope|steam_app_.*)$" }, monitor = asus })

hl.workspace_rule({ workspace = 1, monitor = asus, default = true })
common.apply_dell()
