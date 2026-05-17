-- =============================================================================
-- HARDWARE MULTI-MONITOR DISPLAY LAYOUT CONFIGURATION
-- =============================================================================
-- Map positions, resolutions, refresh rates, scales, and bit-depths.
-- Reference: https://wiki.hypr.land/Configuring/Basics/Monitors/
--
-- Layout Visualization:
-- +-------------------------+-------------------------+
-- |     Dell (Left Top)     |    Asus (Right Top)     |
-- |      (2560 x 1440)      |      (2560 x 1440)      |
-- +-------------------------+-------------------------+
-- |    Sharp (Left Bottom)  |                         |
-- |      (3840 x 2400)      |                         |
-- +-------------------------+-------------------------+

local monitors = {
  -- Primary/Left Monitor (Top row)
  {
    output = "desc:Dell Inc. DELL P2423DE 3PJ4CN3",
    mode = "2560x1440",
    position = "0x0",
    scale = 1
  },
  -- Laptop/Bottom-Left High-DPI Monitor
  {
    output = "desc:Sharp Corporation 0x1516",
    mode = "3840x2400",
    position = "0x1440",                    -- Placed directly below the Dell monitor (Y offset = 1440)
    scale = 2                                 -- UI scaling factor for High-DPI rendering
  },
  -- Secondary/Right Monitor (Top row)
  {
    output = "desc:ASUSTek COMPUTER INC XG32WCS TALMAS012758",
    mode = "2560x1440",
    position = "2560x0",                     -- Placed to the right of the Dell monitor (X offset = 2560)
    scale = 1,
    bitdepth = 10,                            -- High bitdepth (HDR / 10-bit color depth display)
  },
  -- Fallback rule for any newly connected displays
  {
    output = "",
    mode = "preferred",                       -- Automatically pick native resolution
    position = "auto",                        -- Automatically position adjacent to other monitors
    scale = 1
  }
}

-- Register each monitor configuration
for _, monitor in ipairs(monitors) do
  hl.monitor(monitor)
end
