local vars = require("conf.variables")
local mainMod = vars.mainMod

-- Window/Session actions
hl.bind(mainMod .. "+Shift, Q", "killactive")
hl.bind(mainMod .. ", Delete", "exit")
hl.bind(mainMod .. ", W", "togglefloating")
hl.bind("Alt, Return", "fullscreen")
hl.bind(mainMod .. ", L", "exec", "hyprlock -c ~/.config/hypr/hyprlock.conf")
hl.bind("Ctrl+Alt, W", "exec", "killall waybar || waybar")
hl.bind(mainMod .. ", Escape", "exec", "wlogout")

-- Application shortcuts
hl.bind(mainMod .. "+Shift, Return", "exec", "1password")
hl.bind(mainMod .. ", Return", "exec", vars.term)
hl.bind(mainMod .. ", E", "exec", vars.file)
hl.bind(mainMod .. ", C", "exec", vars.editor)
hl.bind(mainMod .. ", F", "fullscreen")
hl.bind(mainMod .. ", D", "exec", vars.menu .. " --show drun")
hl.bind(mainMod .. "+Shift, F", "exec", vars.browser)

hl.bind("ALT, Tab", "cyclenext")
hl.bind("ALT, Tab", "bringactivetotop")

-- Audio control
hl.bindl(", XF86AudioMute", "exec", "swayosd-client --output-volume mute-toggle")
hl.bindl(", XF86AudioMicMute", "exec", "swayosd-client --input-volume mute-toggle")
hl.bindl(", XF86AudioRaiseVolume", "exec", "swayosd-client --output-volume raise")
hl.bindl(", XF86AudioLowerVolume", "exec", "swayosd-client --output-volume lower")

-- Media control
hl.bindl(", XF86AudioPlay", "exec", "playerctl play-pause")
hl.bindl(", XF86AudioPause", "exec", "playerctl play-pause")
hl.bindl(", XF86AudioNext", "exec", "playerctl next")
hl.bindl(", XF86AudioPrev", "exec", "playerctl previous")

-- Brightness control
hl.bindel(", XF86MonBrightnessUp", "exec", "swayosd-client --brightness raise")
hl.bindel(", XF86MonBrightnessDown", "exec", "swayosd-client --brightness lower")

-- Capslock
hl.bindr("CAPS", "Caps_Lock", "exec", "swayosd-client --caps-lock")

-- Grouped windows
hl.bind(mainMod .. " CTRL, H", "changegroupactive", "b")
hl.bind(mainMod .. " CTRL, L", "changegroupactive", "f")

-- Screenshot
hl.bind(mainMod .. ", P", "exec", "grim -g \"$(slurp -d)\" - | swappy -f -")
hl.bind(", Print", "exec", "grim -g \"$(slurp -d)\" - | swappy -f -")

-- Custom scripts
hl.bind(mainMod .. "+Alt, Right", "exec", "~/.dotfiles/bin/swww.sh")
hl.bind(mainMod .. "+Shift, V", "exec", "cliphist list | " .. vars.menu .. " -S dmenu | cliphist decode | wl-copy")

-- Move/Change window focus
hl.bind(mainMod .. ", Left", "movefocus", "l")
hl.bind(mainMod .. ", Right", "movefocus", "r")
hl.bind(mainMod .. ", Up", "movefocus", "u")
hl.bind(mainMod .. ", Down", "movefocus", "d")

-- Switch workspaces
for i = 1, 10 do
    hl.bind(mainMod .. ", " .. i, "workspace", tostring(i))
    hl.bind(mainMod .. "+Shift, " .. i, "movetoworkspace", tostring(i))
end

hl.bind(mainMod .. "+Ctrl, Right", "workspace", "r+1")
hl.bind(mainMod .. "+Ctrl, Left", "workspace", "r-1")
hl.bind(mainMod .. "+Ctrl, Down", "workspace", "empty")

-- Resize windows
hl.binde(mainMod .. "+Shift, Right", "resizeactive", "30 0")
hl.binde(mainMod .. "+Shift, Left", "resizeactive", "-30 0")
hl.binde(mainMod .. "+Shift, Up", "resizeactive", "0 -30")
hl.binde(mainMod .. "+Shift, Down", "resizeactive", "0 30")

-- Move to relative workspace
hl.bind(mainMod .. "+Ctrl+Alt, Right", "movetoworkspace", "r+1")
hl.bind(mainMod .. "+Ctrl+Alt, Left", "movetoworkspace", "r-1")

-- Scroll workspaces
hl.bind(mainMod .. ", mouse_down", "workspace", "e+1")
hl.bind(mainMod .. ", mouse_up", "workspace", "e-1")

-- Move/Resize focused window
hl.bindm(mainMod .. ", mouse:272", "movewindow")
hl.bindm(mainMod .. ", mouse:273", "resizewindow")
