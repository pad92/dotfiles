-- General, Decoration, and Group settings

hl.config({
  general = {
    col = {
      active_border   = "rgba(b4befecc)",
      inactive_border = "rgba(6c7086cc)",
    },
    gaps_in = 1,
    gaps_out = 1,
    border_size = 1,
    layout = "dwindle",
    resize_on_border = true,
  },
  decoration = {
    rounding = 5,
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
        range = 30,
        render_power = 3,
        color = "0x66000000",
    },
  }
})
