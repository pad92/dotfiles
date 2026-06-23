local config = require("config")

hl.config({
  general = {
    layout = config.layout.active_layout,
    resize_on_border = config.layout.resize_on_border,
    col = {
      active_border = config.colors.active_border,
      inactive_border = config.colors.inactive_border,
    },
    gaps_in = config.visuals.gaps_in,
    gaps_out = config.visuals.gaps_out,
    border_size = config.visuals.border_size,
    allow_tearing = true,
  },

  dwindle = config.layout.dwindle,

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
