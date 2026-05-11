hl.curve( myBezier, { type = "bezier", points = { {0, 1}, {0, 1} } })

hl.animation({ leaf = "windows"     , enabled = true, speed = 5, curve = "myBezier" })
hl.animation({ leaf = "windowsOut"  , enabled = true, speed = 5, curve = "default", style = "popin 80%" })
hl.animation({ leaf = "border"      , enabled = true, speed = 8, curve = "default" })
hl.animation({ leaf = "borderangle" , enabled = true, speed = 6, curve = "default" })
hl.animation({ leaf = "fade"        , enabled = true, speed = 5, curve = "default" })
hl.animation({ leaf = "workspaces"  , enabled = true, speed = 5, curve = "default" })
