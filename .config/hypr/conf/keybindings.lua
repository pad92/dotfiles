local vars = require("conf.variables")
local qsIpcCall = "qs -c $qsConfig ipc call"
local qsIsAlive = qsIpcCall .. " TEST_ALIVE"

-- Window/Session actions
hl.bind("SUPER + SHIFT + Q", hl.dsp.window.close(), { description = "Close window" })
hl.bind("SUPER + ALT + Space", hl.dsp.window.float({ action = "toggle" }), { description = "Float/Tile" })
hl.bind("SUPER + F", hl.dsp.window.fullscreen({ "fullscreen" }, { description = "Fullscreen" }))
hl.bind("SUPER + L", hl.dsp.exec_cmd("hyprlock -c ~/.config/hypr/hyprlock.conf"), { description = "Lock" })

hl.bind("SUPER + Delete", hl.dsp.exec_cmd(qsIsAlive .. " || pkill wlogout || wlogout -p layer-shell"))

-- Application shortcuts
hl.bind("SUPER + Return", hl.dsp.exec_cmd(vars.term), { description = "Terminal" })
hl.bind("SUPER + E", hl.dsp.exec_cmd(vars.file), { description = "File manager" })
hl.bind("SUPER + C", hl.dsp.exec_cmd(vars.editor), { description = "Code editor" })
hl.bind("SUPER + W", hl.dsp.exec_cmd(vars.browser), { description = "Browser" })
hl.bind("SUPER + D", hl.dsp.exec_cmd(vars.menu .. " --show drun"), { description = "Application menu" })
hl.bind("SUPER + SHIFT + Return", hl.dsp.exec_cmd("1password"), { description = "1Password" })

-- Focus and Move
local focus_map = {
  { "Left",        "l" }, { "Right", "r" }, { "Up", "u" }, { "Down", "d" },
  { "BracketLeft", "l" }, { "BracketRight", "r" }
}
for _, pair in ipairs(focus_map) do
  hl.bind("SUPER + " .. pair[1], hl.dsp.focus({ direction = pair[2] }))
end

local move_map = {
  { "Left", "l" }, { "Right", "r" }, { "Up", "u" }, { "Down", "d" }
}
for _, pair in ipairs(move_map) do
  hl.bind("SUPER + SHIFT + " .. pair[1], hl.dsp.window.move({ direction = pair[2] }))
end

-- Audio control
hl.bind("XF86AudioMute", hl.dsp.exec_cmd("swayosd-client --output-volume mute-toggle"), { locked = true })
hl.bind("XF86AudioMicMute", hl.dsp.exec_cmd("swayosd-client --input-volume mute-toggle"), { locked = true })
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("swayosd-client --output-volume raise"),
  { locked = true, repeating = true })
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("swayosd-client --output-volume lower"),
  { locked = true, repeating = true })

-- Media control
hl.bind("XF86AudioPlay", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioPause", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioNext", hl.dsp.exec_cmd("playerctl next"), { locked = true })
hl.bind("XF86AudioPrev", hl.dsp.exec_cmd("playerctl previous"), { locked = true })

-- Brightness control
hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd("swayosd-client --brightness raise"), { locked = true, repeating = true })
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("swayosd-client --brightness lower"),
  { locked = true, repeating = true })

-- Capslock
hl.bind("CAPS", hl.dsp.exec_cmd("swayosd-client --caps-lock"), { description = "Caps Lock" })

-- Screenshot
local screenshot_command = "grim -g \"$(slurp -d)\" - | swappy -f -"
hl.bind("Print", hl.dsp.exec_cmd(screenshot_command), { locked = true })
hl.bind("SUPER + P", hl.dsp.exec_cmd(screenshot_command), { locked = true })

-- Custom scripts & Clipboard
hl.bind("SUPER + ALT + Right", hl.dsp.exec_cmd("~/.dotfiles/bin/swww.sh"), { description = "Change wallpaper" })
hl.bind("SUPER + SHIFT + V", hl.dsp.exec_cmd("cliphist list | " .. vars.menu .. " -S dmenu | cliphist decode | wl-copy"),
  { description = "Clipboard history" })

-- Workspaces
for i = 1, 10 do
  local numberkey = { 10, 11, 12, 13, 14, 15, 16, 17, 18, 19 }
  hl.bind("SUPER + ALT + code:" .. numberkey[i], hl.dsp.window.move({ workspace = i, follow = false }))
end
--# keypad numbers
for i = 1, 10 do
  local numpadkey = { 87, 88, 89, 83, 84, 85, 79, 80, 81, 90 }
  hl.bind("SUPER + ALT + code:" .. numpadkey[i], hl.dsp.window.move({ workspace = i, follow = false }))
end

hl.bind("CTRL + SUPER + Right", hl.dsp.focus({ workspace = "r+1" }))
hl.bind("CTRL + SUPER + Left", hl.dsp.focus({ workspace = "r-1" }))

for i = 1, 9 do
  hl.bind("SUPER + " .. i, hl.dsp.focus({ workspace = i }))
end

-- Mouse bindings
hl.bind("SUPER + mouse:272", hl.dsp.window.drag(), { mouse = true, description = "Move window" })
hl.bind("SUPER + mouse:273", hl.dsp.window.resize(), { mouse = true, description = "Resize window" })
