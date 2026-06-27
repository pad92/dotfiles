local config = require("config")

-- Session & window management
hl.bind(config.mainMod .. " + SHIFT + Q", hl.dsp.window.close(), { description = "Close window" })
hl.bind("ALT + Tab", hl.dsp.focus({ window = "next" }), { repeating = true, description = "Cycle next window" })
hl.bind("ALT + Tab", hl.dsp.window.bring_to_top(), { repeating = true, description = "Bring active to top" })
hl.bind(config.mainMod .. " + ALT + Space", hl.dsp.window.float({ action = "toggle" }), { description = "Float/Tile" })
hl.bind(config.mainMod .. " + F", hl.dsp.window.fullscreen({ "fullscreen" }), { description = "Fullscreen" })
hl.bind(config.mainMod .. " + L", hl.dsp.exec_cmd(config.utils.lock), { description = "Lock" })
hl.bind(config.mainMod .. " + Delete", hl.dsp.exec_cmd(config.utils.logout))

-- Application shortcuts
hl.bind(config.mainMod .. " + Return", hl.dsp.exec_cmd(config.apps.term), { description = "Terminal" })
hl.bind(config.mainMod .. " + E", hl.dsp.exec_cmd(config.apps.file), { description = "File manager" })
hl.bind(config.mainMod .. " + C", hl.dsp.exec_cmd(config.apps.editor), { description = "Code editor" })
hl.bind(config.mainMod .. " + W", hl.dsp.exec_cmd(config.apps.browser), { description = "Browser" })
hl.bind(config.mainMod .. " + M", hl.dsp.exec_cmd(config.apps.music), { description = "Music Player" })
hl.bind(config.mainMod .. " + D", hl.dsp.exec_cmd(config.apps.menu .. " -t"), { description = "Application menu" })
hl.bind(
  config.mainMod .. " + SHIFT + Return",
  hl.dsp.exec_cmd(config.apps.password_manager),
  { description = "Password Manager" }
)

-- Focus & move
local focus_map = {
  { "Left", "l" },
  { "Right", "r" },
  { "Up", "u" },
  { "Down", "d" },
  { "BracketLeft", "l" },
  { "BracketRight", "r" },
}
for _, pair in ipairs(focus_map) do
  hl.bind(config.mainMod .. " + " .. pair[1], hl.dsp.focus({ direction = pair[2] }))
end

for _, pair in ipairs({ { "Left", "l" }, { "Right", "r" }, { "Up", "u" }, { "Down", "d" } }) do
  hl.bind(config.mainMod .. " + SHIFT + " .. pair[1], hl.dsp.window.move({ direction = pair[2] }))
end

-- Audio & media
hl.bind("XF86AudioMute", hl.dsp.exec_cmd(config.utils.vol_mute), { locked = true })
hl.bind("XF86AudioMicMute", hl.dsp.exec_cmd(config.utils.mic_mute), { locked = true })
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd(config.utils.vol_up), { locked = true, repeating = true })
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd(config.utils.vol_down), { locked = true, repeating = true })
hl.bind("XF86AudioPlay", hl.dsp.exec_cmd(config.utils.media_play_pause), { locked = true })
hl.bind("XF86AudioPause", hl.dsp.exec_cmd(config.utils.media_play_pause), { locked = true })
hl.bind("XF86AudioNext", hl.dsp.exec_cmd(config.utils.media_next), { locked = true })
hl.bind("XF86AudioPrev", hl.dsp.exec_cmd(config.utils.media_prev), { locked = true })

-- Brightness & caps lock
hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd(config.utils.bright_up), { locked = true, repeating = true })
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd(config.utils.bright_down), { locked = true, repeating = true })
hl.bind("CAPS", hl.dsp.exec_cmd(config.utils.caps_lock), { description = "Caps Lock" })

-- Screenshot
hl.bind("Print", hl.dsp.exec_cmd(config.utils.screenshot), { locked = true })
hl.bind(config.mainMod .. " + P", hl.dsp.exec_cmd(config.utils.screenshot), { locked = true })

-- Wallpaper & clipboard
hl.bind(
  config.mainMod .. " + ALT + Right",
  hl.dsp.exec_cmd(config.utils.wallpaper),
  { description = "Change wallpaper" }
)
hl.bind(
  config.mainMod .. " + SHIFT + V",
  hl.dsp.exec_cmd(string.format(config.utils.clipboard, config.apps.menu)),
  { description = "Clipboard history" }
)

-- Workspace management
local NUMBER_KEYS = { 10, 11, 12, 13, 14, 15, 16, 17, 18, 19 }
local NUMPAD_KEYS = { 87, 88, 89, 83, 84, 85, 79, 80, 81, 90 }

for i = 1, 10 do
  local key = i == 10 and "0" or tostring(i)
  hl.bind(config.mainMod .. " + " .. key, hl.dsp.focus({ workspace = i }))
  hl.bind(config.mainMod .. " + SHIFT + " .. key, hl.dsp.window.move({ workspace = i, follow = true }))
  hl.bind(config.mainMod .. " + ALT + code:" .. NUMBER_KEYS[i], hl.dsp.window.move({ workspace = i, follow = false }))
  hl.bind(config.mainMod .. " + ALT + code:" .. NUMPAD_KEYS[i], hl.dsp.window.move({ workspace = i, follow = false }))
end

hl.bind("CTRL + SUPER + Right", hl.dsp.focus({ workspace = "r+1" }))
hl.bind("CTRL + SUPER + Left", hl.dsp.focus({ workspace = "r-1" }))

-- Mouse bindings
hl.bind(config.mainMod .. " + mouse:272", hl.dsp.window.drag(), { mouse = true, description = "Move window" })
hl.bind(config.mainMod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true, description = "Resize window" })

-- Screen zoom (SUPER + PgUp/PgDn, Home resets)
hl.bind(
  config.mainMod .. " + Page_Up",
  hl.dsp.exec_cmd(config.utils.zoom_in),
  { repeating = true, description = "Zoom in" }
)
hl.bind(
  config.mainMod .. " + Page_Down",
  hl.dsp.exec_cmd(config.utils.zoom_out),
  { repeating = true, description = "Zoom out" }
)
hl.bind(config.mainMod .. " + Home", hl.dsp.exec_cmd(config.utils.zoom_reset), { description = "Reset zoom" })
