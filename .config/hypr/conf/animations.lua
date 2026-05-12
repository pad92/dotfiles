-- Animations configuration
hl.curve("myBezier", { type = "bezier", points = { {0, 1}, {1, 1} } })

hl.animation({ leaf = "windows",     enabled = true, speed = 5, bezier = "myBezier" })
hl.animation({ leaf = "windowsOut",  enabled = true, speed = 5, bezier = "myBezier", style = "popin 80%" })
hl.animation({ leaf = "border",      enabled = true, speed = 8, bezier = "myBezier" })
hl.animation({ leaf = "borderangle", enabled = true, speed = 6, bezier = "myBezier" })
hl.animation({ leaf = "fade",        enabled = true, speed = 5, bezier = "myBezier" })
hl.animation({ leaf = "workspaces",  enabled = true, speed = 5, bezier = "myBezier" })
