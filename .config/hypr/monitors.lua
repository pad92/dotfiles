-- https://wiki.hypr.land/Configuring/Basics/Monitors/

-- Layout:
-- +-------------------+-------------------+
-- |       Dell        |       Asus        |
-- |   (2560 x 1440)   |   (2560 x 1440)   |
-- +-------------------+-------------------+
-- |       Sharp       |                   |
-- |   (3840 x 2400)   |                   |
-- +-------------------+-------------------+

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
  {
    output = "desc:ASUSTek COMPUTER INC XG32WCS TALMAS012758",
    mode = "2560x1440",
    position = "2560x0",
    scale = 1,
    bitdepth = 10,
  },
  {
    output = "",
    mode = "preferred",
    position = "auto",
    scale = 1
  }
}

for _, monitor in ipairs(monitors) do
  hl.monitor(monitor)
end
