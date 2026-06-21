-- =============================================================================
-- KEYBOARD, MOUSE & GESTURES CONFIGURATION
-- =============================================================================
-- Defines keyboard layouts, mouse sensitivities, and trackpad gestures.

local config = require("config")

hl.config({
  -- Keyboard & general mouse input settings
  input = {
    kb_layout = config.input.kb_layout,
    kb_variant = config.input.kb_variant,
    follow_mouse = config.input.follow_mouse,
    numlock_by_default = config.input.numlock_by_default,
    sensitivity = config.input.sensitivity,
    touchpad = config.input.touchpad,
  },

  -- Mouse Cursor preferences
  cursor = config.input.cursor,

  -- Touch/Trackpad Swipe gestures for workspace switching
  gestures = config.input.gestures,
})

-- Device-specific overrides (for mice, keyboards, touchpads, etc.)
-- Reference: https://wiki.hypr.land/Configuring/Advanced-and-Cool/Devices/
if config.input.device_overrides.name then
  hl.device(config.input.device_overrides)
end
