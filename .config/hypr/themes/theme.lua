-- Theme specific settings

hl.config({ general = {
    gaps_in = 4,
    gaps_out = 5,
    border_size = 1,
    -- col_active_border = "rgba(44464f77)",
    -- col_inactive_border = "rgba(1a1b2033)",
    layout = "dwindle",
    resize_on_border = true,
}})

-- hl.config({ group_snap = {
--     enabled = true,
--     window_gap = 4,
--     monitor_gap = 5,
-- }})

hl.config({ decoration = {
    rounding = 18,
    blur = {
        enabled = true,
        size = 10,
        passes = 3,
        new_optimizations = true,
        ignore_opacity = true,
        xray = true,
    },
    shadow = {
        enabled = true,
        range = 20,
        render_power = 10,
        color = "rgba(00000020)",
    },
}})

-- hl.config({ group = {
--     col_border_active = "rgba(44464f77)",
--     col_border_inactive = "rgba(1a1b2033)",
--     col_border_locked_active = "rgba(44464f77)",
--     col_border_locked_inactive = "rgba(1a1b2033)",
-- }})
