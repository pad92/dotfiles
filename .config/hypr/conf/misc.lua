-- General, Decoration, and Group settings

hl.general({
    gaps_in = 1,
    gaps_out = 1,
    border_size = 1,
    col_active_border = "rgba(ca9ee6ff) rgba(f2d5cfff) 45deg",
    col_inactive_border = "rgba(b4befecc) rgba(6c7086cc) 45deg",
    layout = "dwindle",
    resize_on_border = true,
})

hl.general_snap({
    enabled = true,
    window_gap = 25,
    monitor_gap = 10,
})

hl.decoration({
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
})

hl.group({
    col_border_active = "rgba(ca9ee6ff) rgba(f2d5cfff) 45deg",
    col_border_inactive = "rgba(b4befecc) rgba(6c7086cc) 45deg",
    col_border_locked_active = "rgba(ca9ee6ff) rgba(f2d5cfff) 45deg",
    col_border_locked_inactive = "rgba(b4befecc) rgba(6c7086cc) 45deg",
})
