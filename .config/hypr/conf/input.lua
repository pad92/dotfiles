-- =============================================================================
-- KEYBOARD, MOUSE & GESTURES CONFIGURATION
-- =============================================================================
-- Defines keyboard layouts, mouse sensitivities, and trackpad gestures.

local config = require("config")

hl.config({
  -- Keyboard & general mouse input settings
  input = {
    kb_layout = config.input.kb_layout,     -- US Keyboard Layout
    kb_variant = config.input.kb_variant,   -- US International variant (enables dead-key accents)
    follow_mouse = 1,                       -- Window focus follows the mouse movement
    numlock_by_default = true,              -- Enables Num Lock on startup
    sensitivity = 0,                        -- Default system pointer sensitivity (-1.0 to 1.0)

    -- Laptop Touchpad / Trackpad configuration
    touchpad = {
        natural_scroll = false,             -- True enables reverse scrolling (like macOS)
        tap_to_click = true,                -- Enables primary click on tap
        disable_while_typing = true,        -- Disables trackpad to prevent accidental clicks while typing
        scroll_factor = 0.5,                -- Trackpad scroll speed multiplier
        tap_and_drag = true,                -- Enables tap, lift, and immediate drag action
        drag_lock = false,                  -- Keeps dragging even if finger is briefly lifted
    },
  },

  -- Mouse Cursor preferences
  cursor = {
    no_hardware_cursors = true,             -- Hardware cursor acceleration
    enable_hyprcursor = true,               -- Activates modern high-DPI hyprcursor support
  },

  -- Touch/Trackpad Swipe gestures for workspace switching
  gestures = {
      workspace_swipe_distance = 500,       -- Swipe travel distance required to switch workspaces (pixels)
      workspace_swipe_invert = true,        -- Inverts the swipe direction to feel more natural
      workspace_swipe_min_speed_to_force = 30, -- Speed threshold to force transition even if distance is short
      workspace_swipe_cancel_ratio = 0.5,   -- Percentage of swipe required before it doesn't snap back on cancel
      workspace_swipe_create_new = true,     -- Creates a new workspace if swiping past the last one
      workspace_swipe_forever = true,       -- Allows endless continuous swiping across multiple workspaces
  }
})

-- Device-specific overrides (for mice, keyboards, touchpads, etc.)
-- Reference: https://wiki.hypr.land/Configuring/Advanced-and-Cool/Devices/
hl.device = ({
    name = "epic mouse V1",
    sensitivity = -0.5,                     -- Lowers sensitivity specifically for this hardware mouse
})
