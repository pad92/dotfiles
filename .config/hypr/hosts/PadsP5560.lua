local hl = rawget(_G, "hl")
local common = require("hosts.common")

local monitors = {
  {
    output = "desc:Sharp Corporation 0x1516",
    mode = "3840x2400",
    position = "0x1440",
    scale = 2,
  },
  common.asus_monitor("2560x1440@60"), -- capped for productivity
}

hl.monitor(common.dell_monitor)
for _, monitor in ipairs(monitors) do
  hl.monitor(monitor)
end

hl.config({
  decoration = {
    blur = { enabled = false },
    shadow = { enabled = false },
  },
})

hl.workspace_rule({ workspace = 1, monitor = common.asus_output, default = true })
common.apply_dell()
hl.workspace_rule({ workspace = 8, monitor = "desc:Sharp Corporation 0x1516", default = true })
