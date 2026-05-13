-- General, Decoration, and Group settings
local config = require("config")

hl.config({
  general = {
    col = {
      active_border   = config.active_border,
      inactive_border = config.inactive_border,
    },
    gaps_in = 1,
    gaps_out = 1,
    border_size = 1,
    layout = "dwindle",
    resize_on_border = true,
  },
  decoration = {
        rounding_power = 2.5,
        rounding = 10,
    blur = {
        enabled = true,
        size = 6,
        passes = 2,
        new_optimizations = true,
        ignore_opacity = true,
        xray = true,
    },
    shadow = {
        enabled = true,
        range = 20,
        offset = {0, 2},
        render_power = 10,
        color = "rgba(00000020)"
    },
  }
})
