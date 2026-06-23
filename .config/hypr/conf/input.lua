local config = require("config")

hl.config({
  input = {
    kb_layout = config.input.kb_layout,
    kb_variant = config.input.kb_variant,
    follow_mouse = config.input.follow_mouse,
    numlock_by_default = config.input.numlock_by_default,
    sensitivity = config.input.sensitivity,
    touchpad = config.input.touchpad,
  },
  cursor = config.input.cursor,
  gestures = config.input.gestures,
})

if config.input.device_overrides.name then
  hl.device(config.input.device_overrides)
end
