-- Input configuration
hl.config({
  input = {
    kb_layout = "us",
    kb_variant = "intl",
    follow_mouse = 1,
    numlock_by_default = true,
    sensitivity = 0,
    touchpad = {
        natural_scroll = false,
        tap_to_click = true,
        disable_while_typing = true,
        scroll_factor = 0.5,
        tap_and_drag = true,
        drag_lock = false,
    },
  },
  cursor = {
    no_hardware_cursors = false,
    enable_hyprcursor = true,
  },
  gestures = {
      workspace_swipe_distance = 500,
      workspace_swipe_invert = true,
      workspace_swipe_min_speed_to_force = 30,
      workspace_swipe_cancel_ratio = 0.5,
      workspace_swipe_create_new = true,
      workspace_swipe_forever = true,
}})

-- Device specific settings
-- https://wiki.hypr.land/Configuring/Advanced-and-Cool/Devices/
hl.device = ({
    name = "epic mouse V1",
    sensitivity = -0.5,
})
