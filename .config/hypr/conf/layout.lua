-- =============================================================================
-- WINDOW LAYOUT ALGORITHM CONFIGURATION (DWINDLE)
-- =============================================================================
-- Configures properties for the Dwindle tiling layout.

local config = require("config")

hl.config({ 
  general = {
    layout = config.layout.active_layout,
    resize_on_border = config.layout.resize_on_border,
  },
  dwindle = config.layout.dwindle,
})
