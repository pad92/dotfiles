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
    layout = "dwindle",                                -- Default window partitioning algorithm
    resize_on_border = true,                           -- Allows resizing windows by dragging their borders
    allow_tearing = true,                              -- Master toggle for screen tearing
  },

  -- Window decorations (Rounding, Blur, Shadows)
  decoration = {
    rounding_power = 2.5,                       -- Corner curvature math factor
    rounding = config.visuals.rounding,         -- Radius of rounded corners in pixels

    -- Glassmorphism blur settings
    blur = {
      enabled = true,                           -- Enables active background blur
      size = 6,                                 -- Blur radius
      passes = 2,                               -- Number of blur rendering passes
      new_optimizations = true,                 -- Performs faster rendering for background blur
      ignore_opacity = true,                    -- Blurs the area regardless of window transparency
      xray = true,                              -- Optimizes blur passes by drawing directly on the layer beneath
    },

    -- Drop shadow settings
    shadow = {
      enabled = true,                           -- Enables soft drop shadows under windows
      range = 20,                               -- Blur radius of the shadows
      offset = {0, 2},                          -- Position offset of shadows (X, Y)
      render_power = 10,                        -- Density and strength of the shadow decay
      color = config.colors.shadow              -- Color of the drop shadows
    },
  }
})
