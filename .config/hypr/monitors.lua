-- https://wiki.hypr.land/Configuring/Basics/Monitors/

hl.monitor({
  output = "desc:Sharp Corporation 0x1516",
    mode = "3840x2400",
    position = "0x1440",
    scale = 2
  },{
  output = "desc:Dell Inc. DELL P2423DE 3PJ4CN3",
    mode = "2560x1440",
    position = "0x0",
    scale = 1
  },{
  output = "desc:ASUSTek COMPUTER INC XG32WCS TALMAS012758",
    mode = "2560x1440",
    position = "2560x0",
    bitdepth = 10,
    scale = 1,
  },{
  output = "",
    mode = "preferred",
    position = "auto",
    scale = 1,
})
