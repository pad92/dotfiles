-- =============================================================================
-- HARDWARE MULTI-MONITOR DISPLAY LAYOUT CONFIGURATION
-- =============================================================================
-- Map positions, resolutions, refresh rates, scales, and bit-depths.
-- Reference: https://wiki.hypr.land/Configuring/Basics/Monitors/

local monitors = {
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
