-- Animations configuration
local my_bezier = "myBezier"
hl.curve(my_bezier, { type = "bezier", points = { { 0, 1 }, { 0, 1 } } })

-- Animation settings: { leaf = "name", speed = value, style = "optional_style" }
local anim_settings = {
  { leaf = "windows",     speed = 5 },
  { leaf = "windowsOut",  speed = 5, style = "popin 80%" },
  { leaf = "border",      speed = 8 },
  { leaf = "borderangle", speed = 6 },
  { leaf = "fade",        speed = 5 },
  { leaf = "workspaces",  speed = 5 },
}

for _, anim in ipairs(anim_settings) do
  hl.animation({
    leaf = anim.leaf,
    enabled = true,
    speed = anim.speed,
    bezier = my_bezier,
    style = anim.style
  })
end
