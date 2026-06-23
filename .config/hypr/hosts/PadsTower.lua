local monitors = {
  {
    output = "desc:Dell Inc. DELL P2423DE 3PJ4CN3",
    mode = "2560x1440",
    position = "0x0",
    scale = 1
  },
  {
    output = "desc:ASUSTek COMPUTER INC XG32WCS TALMAS012758",
    mode = "2560x1440@144",
    position = "2560x0",
    scale = 1,
    bitdepth = 10,
  }
}

for _, monitor in ipairs(monitors) do
  hl.monitor(monitor)
end

-- Route Steam/games to the ASUS monitor
local asus = "desc:ASUSTek COMPUTER INC XG32WCS TALMAS012758"
hl.window_rule({ match = { class = "^(?i)(steam)$", title = "^(?i)(Steam Big Picture Mode)$" }, monitor = asus })
hl.window_rule({ match = { class = "^(?i)(gamescope|steam_app_.*)$" }, monitor = asus })

hl.workspace_rule({ workspace = 1, monitor = asus, default = true })
hl.workspace_rule({ workspace = 2, monitor = "desc:Dell Inc. DELL P2423DE 3PJ4CN3", default = true })
