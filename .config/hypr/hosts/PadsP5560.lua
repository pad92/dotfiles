local monitors = {
  {
    output = "desc:Dell Inc. DELL P2423DE 3PJ4CN3",
    mode = "2560x1440",
    position = "0x0",
    scale = 1
  },
  {
    output = "desc:Sharp Corporation 0x1516",
    mode = "3840x2400",
    position = "0x1440",
    scale = 2
  },
  -- Capped at 60Hz for productivity
  {
    output = "desc:ASUSTek COMPUTER INC XG32WCS TALMAS012758",
    mode = "2560x1440@60",
    position = "2560x0",
    scale = 1,
    bitdepth = 10,
  }
}

for _, monitor in ipairs(monitors) do
  hl.monitor(monitor)
end

hl.config({
  decoration = {
    blur = { enabled = false },
    shadow = { enabled = false },
  },
})

hl.workspace_rule({ workspace = 1, monitor = "desc:ASUSTek COMPUTER INC XG32WCS TALMAS012758", default = true })
hl.workspace_rule({ workspace = 2, monitor = "desc:Dell Inc. DELL P2423DE 3PJ4CN3", default = true })
hl.workspace_rule({ workspace = 8, monitor = "desc:Sharp Corporation 0x1516", default = true })
