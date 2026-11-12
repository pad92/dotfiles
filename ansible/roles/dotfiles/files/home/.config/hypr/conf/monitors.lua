local hl = rawget(_G, "hl")

-- Fallback rule for any connected display: Hyprland picks the mode, the scale
-- from the panel's density and the position. include/host.lua then places the
-- monitors that hosts/settings.lua knows next to each other.
hl.monitor({
  output = "",
  mode = "preferred",
  position = "auto",
  scale = "auto",
})
