-- =============================================================================
-- HYPRLAND APPEARANCE CONFIGURATION (GENERAL, DECORATION, SHADOWS)
-- =============================================================================
-- Configures colors, margins, rounding, borders, blur effects, and drop shadows.

local config = require("config")

hl.config({
  -- Core layout, borders, and margins
  general = {
    col = {
      active_border = config.colors.active_border,     -- Border color for focused windows
      inactive_border = config.colors.inactive_border, -- Border color for unfocused windows
    },
    gaps_in = config.visuals.gaps_in,                  -- Margins between adjacent windows
    gaps_out = config.visuals.gaps_out,                -- Margins between windows and screen edges
    border_size = config.visuals.border_size,          -- Thickness of window borders
    layout = config.layout.active_layout,              -- Default window partitioning algorithm
    resize_on_border = config.layout.resize_on_border,  -- Allows resizing windows by dragging their borders
    allow_tearing = true,                              -- Master toggle for screen tearing
  },

  -- Window decorations (Rounding, Blur, Shadows)
  decoration = {
    rounding_power = config.visuals.rounding_power,     -- Corner curvature math factor
    rounding = config.visuals.rounding,                 -- Radius of rounded corners in pixels
    blur = config.visuals.blur,                         -- Glassmorphism blur settings
    shadow = {
      enabled = config.visuals.shadow.enabled,          -- Enables soft drop shadows under windows
      range = config.visuals.shadow.range,              -- Blur radius of the shadows
      offset = config.visuals.shadow.offset,            -- Position offset of shadows (X, Y)
      render_power = config.visuals.shadow.render_power,-- Density and strength of the shadow decay
      color = config.colors.shadow                      -- Color of the drop shadows
    },
  }
})
