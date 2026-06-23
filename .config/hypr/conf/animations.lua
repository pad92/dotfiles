local my_bezier = "myBezier"
hl.curve(my_bezier, { type = "bezier", points = { { 0, 1 }, { 0, 1 } } })

local anim_settings = {
  { leaf = "windows",     speed = 8 },
  { leaf = "windowsOut",  speed = 8, style = "popin 80%" },
  { leaf = "border",      speed = 10 },
  { leaf = "fade",        speed = 8 },
  { leaf = "workspaces",  speed = 7 },
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
