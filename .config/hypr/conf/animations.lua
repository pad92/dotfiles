-- Curves mirror Hyprland's official example/hyprland.lua.
hl.curve("easeOutQuint", { type = "bezier", points = { { 0.23, 1 }, { 0.32, 1 } } })
hl.curve("linear", { type = "bezier", points = { { 0, 0 }, { 1, 1 } } })
hl.curve("almostLinear", { type = "bezier", points = { { 0.5, 0.5 }, { 0.75, 1 } } })
hl.curve("quick", { type = "bezier", points = { { 0.15, 0 }, { 0.1, 1 } } })
hl.curve("easy", { type = "spring", mass = 1, stiffness = 71.2633, dampening = 15.8273644 })

local anim_settings = {
  { leaf = "windows", speed = 4.79, spring = "easy" },
  { leaf = "windowsIn", speed = 4.1, spring = "easy", style = "popin 87%" },
  { leaf = "windowsOut", speed = 1.49, bezier = "linear", style = "popin 80%" },
  { leaf = "border", speed = 5.39, bezier = "easeOutQuint" },
  { leaf = "fade", speed = 3.03, bezier = "quick" },
  { leaf = "workspaces", speed = 1.94, bezier = "almostLinear", style = "fade" },
  { leaf = "layers", speed = 3.81, bezier = "easeOutQuint" },
  { leaf = "layersIn", speed = 4, bezier = "easeOutQuint", style = "fade" },
  { leaf = "layersOut", speed = 1.5, bezier = "linear", style = "fade" },
  { leaf = "fadeLayersIn", speed = 1.79, bezier = "almostLinear" },
  { leaf = "fadeLayersOut", speed = 1.39, bezier = "almostLinear" },
  { leaf = "zoomFactor", speed = 7, bezier = "quick" },
}

for _, anim in ipairs(anim_settings) do
  hl.animation({
    leaf = anim.leaf,
    enabled = true,
    speed = anim.speed,
    bezier = anim.bezier,
    spring = anim.spring,
    style = anim.style,
  })
end
