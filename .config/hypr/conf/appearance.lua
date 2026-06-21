-- =============================================================================
-- HYPRLAND APPEARANCE CONFIGURATION (GENERAL, DECORATION, SHADOWS)
-- =============================================================================
-- Configures colors, margins, rounding, borders, blur effects, and drop shadows.

local config = require("config")

hl.config({
  -- Core layout, borders, and margins
  general = {
    col = {
      active_border = config.colors.active_border,
      inactive_border = config.colors.inactive_border,
    },
    gaps_in = config.visuals.gaps_in,
    gaps_out = config.visuals.gaps_out,
    border_size = config.visuals.border_size,
    allow_tearing = true,
  },

  -- Window decorations (Rounding, Blur, Shadows)
  decoration = {
    rounding_power = config.visuals.rounding_power,
    rounding = config.visuals.rounding,
    blur = config.visuals.blur,
    shadow = {
      enabled = config.visuals.shadow.enabled,
      range = config.visuals.shadow.range,
      offset = config.visuals.shadow.offset,
      render_power = config.visuals.shadow.render_power,
      color = config.colors.shadow,
    },
  }
})
