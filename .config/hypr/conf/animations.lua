-- =============================================================================
-- HYPRLAND ANIMATIONS CONFIGURATION
-- =============================================================================
-- Defines window transitions, fades, and workspace switching speeds and curves.

-- Define custom cubic Bezier curves for smooth animation curves
local my_bezier = "myBezier"
hl.curve(my_bezier, { type = "bezier", points = { { 0, 1 }, { 0, 1 } } })

-- Define animation settings for different UI elements
-- Structure: { leaf = "element_name", speed = duration_multiplier, style = "optional_animation_style" }
local anim_settings = {
  { leaf = "windows",     speed = 5 },                  -- Opening/closing of windows
  { leaf = "windowsOut",  speed = 5, style = "popin 80%" }, -- Closing transitions (scale down to 80%)
  { leaf = "border",      speed = 8 },                  -- Border color transition speed
  { leaf = "borderangle", speed = 6 },                  -- Rotating border gradient speed
  { leaf = "fade",        speed = 5 },                  -- Fade-in/out transitions
  { leaf = "workspaces",  speed = 5 },                  -- Workspace switching speed
}

-- Apply the animation configuration to each element
for _, anim in ipairs(anim_settings) do
  hl.animation({
    leaf = anim.leaf,
    enabled = true,
    speed = anim.speed,
    bezier = my_bezier,
    style = anim.style
  })
end
