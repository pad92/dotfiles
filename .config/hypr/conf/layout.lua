-- =============================================================================
-- WINDOW LAYOUT ALGORITHM CONFIGURATION (DWINDLE)
-- =============================================================================
-- Configures properties for the Dwindle tiling layout.

hl.config({ 
  dwindle = {
    preserve_split = true,       -- Keeps split orientation constant when moving/removing windows
    smart_split = false,         -- Auto-determines window splitting direction based on cursor position
    smart_resizing = false,      -- Dynamic proportional window resizing
    -- precise_mouse_move = true, -- Precision window positioning when dragging
  }
})
