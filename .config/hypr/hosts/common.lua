local hl = rawget(_G, "hl")

-- Shared config across hosts: both PadsTower and PadsP5560 drive the same
-- external Dell and ASUS monitors, so the common parts are factored here
-- instead of being duplicated verbatim in each hosts/<hostname>.lua.
local M = {}

M.dell_monitor = {
  output = "desc:Dell Inc. DELL P2423DE 3PJ4CN3",
  mode = "2560x1440",
  position = "0x0",
  scale = 1,
}

function M.apply_dell()
  hl.monitor(M.dell_monitor)
  hl.workspace_rule({ workspace = 2, monitor = M.dell_monitor.output, default = true })
end

M.asus_output = "desc:ASUSTek COMPUTER INC XG32WCS TALMAS012758"

-- Refresh rate is host-specific (144Hz on PadsTower, capped at 60Hz for
-- productivity on PadsP5560), so it's the only part passed in.
function M.asus_monitor(mode)
  return {
    output = M.asus_output,
    mode = mode,
    position = "2560x0",
    scale = 1,
  }
end

return M
