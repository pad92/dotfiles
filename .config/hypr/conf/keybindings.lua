-- =============================================================================
-- HYPRLAND KEYBINDINGS CONFIGURATION
-- =============================================================================
-- Sets up key shortcuts for session actions, system utilities, and application launches.

local config = require("config")

-- =============================================================================
-- SESSION & WINDOW MANAGEMENT ACTIONS
-- =============================================================================

-- Close the currently focused window
hl.bind(config.mainMod .. " + SHIFT + Q", hl.dsp.window.close(), { description = "Close window" })

-- Cycle through windows and bring the active one to top (ALT + Tab)
hl.bind("ALT + Tab", hl.dsp.focus({ window = "next" }), { repeating = true, description = "Cycle next window" })
hl.bind("ALT + Tab", hl.dsp.window.bring_to_top(), { repeating = true, description = "Bring active to top" })

-- Toggle the active window between Floating and Tiled modes
hl.bind(config.mainMod .. " + ALT + Space", hl.dsp.window.float({ action = "toggle" }), { description = "Float/Tile" })

-- Toggle active window to fullscreen mode
hl.bind(config.mainMod .. " + F", hl.dsp.window.fullscreen({ "fullscreen" }, { description = "Fullscreen" }))

-- Lock the display session using hyprlock
hl.bind(config.mainMod .. " + L", hl.dsp.exec_cmd(config.utils.lock), { description = "Lock" })

-- Session logout menu (tries to signal quickshell widget, falls back to wlogout overlay)
hl.bind(config.mainMod .. " + Delete", hl.dsp.exec_cmd(config.utils.logout))

-- =============================================================================
-- APPLICATION SHORTCUTS (configured in config.lua)
-- =============================================================================

-- Open primary terminal emulator (Alacritty)
hl.bind(config.mainMod .. " + Return", hl.dsp.exec_cmd(config.apps.term), { description = "Terminal" })

-- Launch default file manager (Nautilus)
hl.bind(config.mainMod .. " + E", hl.dsp.exec_cmd(config.apps.file), { description = "File manager" })

-- Launch preferred code editor (VS Codium)
hl.bind(config.mainMod .. " + C", hl.dsp.exec_cmd(config.apps.editor), { description = "Code editor" })

-- Launch default web browser (Firefox)
hl.bind(config.mainMod .. " + W", hl.dsp.exec_cmd(config.apps.browser), { description = "Browser" })

-- Toggle the window between focus and float
hl.bind(config.mainMod .. " + SHIFT + F", hl.dsp.window.float({ action = "toggle" }), { description = "Toggle Float" })

-- Launch default music player (Spotify)
hl.bind(config.mainMod .. " + M", hl.dsp.exec_cmd(config.apps.music), { description = "Music Player" })

-- Toggle the Wofi application launcher menu
hl.bind(config.mainMod .. " + D", hl.dsp.exec_cmd(config.apps.menu .. " --show drun"), { description = "Application menu" })

-- Open password manager
hl.bind(config.mainMod .. " + SHIFT + Return", hl.dsp.exec_cmd(config.apps.password_manager), { description = "Password Manager" })

-- =============================================================================
-- NAVIGATION & DÉPLACEMENT (FOCUS & MOVE)
-- =============================================================================

-- Focus adjacent window (supports Arrow keys, l/r/u/d keys, and Bracket Left/Right)
local focus_map = {
  { "Left",        "l" }, { "Right", "r" }, { "Up", "u" }, { "Down", "d" },
  { "BracketLeft", "l" }, { "BracketRight", "r" }
}
for _, pair in ipairs(focus_map) do
  hl.bind(config.mainMod .. " + " .. pair[1], hl.dsp.focus({ direction = pair[2] }))
end

-- Move focused window within active workspace (supports Arrow keys or l/r/u/d keys)
local move_map = {
  { "Left", "l" }, { "Right", "r" }, { "Up", "u" }, { "Down", "d" }
}
for _, pair in ipairs(move_map) do
  hl.bind(config.mainMod .. " + SHIFT + " .. pair[1], hl.dsp.window.move({ direction = pair[2] }))
end

-- =============================================================================
-- AUDIO CONTROLS (swayosd-client & playerctl)
-- =============================================================================

-- Toggle sound mute status
hl.bind("XF86AudioMute", hl.dsp.exec_cmd(config.utils.vol_mute), { locked = true })

-- Toggle microphone mute status
hl.bind("XF86AudioMicMute", hl.dsp.exec_cmd(config.utils.mic_mute), { locked = true })

-- Raise system audio volume (repeats on hold, locked when display is locked)
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd(config.utils.vol_up),
  { locked = true, repeating = true })

-- Lower system audio volume (repeats on hold, locked when display is locked)
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd(config.utils.vol_down),
  { locked = true, repeating = true })

-- Media playback controls using playerctl daemon
hl.bind("XF86AudioPlay", hl.dsp.exec_cmd(config.utils.media_play_pause), { locked = true })
hl.bind("XF86AudioPause", hl.dsp.exec_cmd(config.utils.media_play_pause), { locked = true })
hl.bind("XF86AudioNext", hl.dsp.exec_cmd(config.utils.media_next), { locked = true })
hl.bind("XF86AudioPrev", hl.dsp.exec_cmd(config.utils.media_prev), { locked = true })

-- =============================================================================
-- DISPLAY BRIGHTNESS & CAPS LOCK OVERLAYS
-- =============================================================================

-- Increase monitor brightness using SwayOSD
hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd(config.utils.bright_up), { locked = true, repeating = true })

-- Decrease monitor brightness using SwayOSD
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd(config.utils.bright_down),
  { locked = true, repeating = true })

-- Toggle Caps Lock state with an overlay notification
hl.bind("CAPS", hl.dsp.exec_cmd(config.utils.caps_lock), { description = "Caps Lock" })

-- =============================================================================
-- SCREENSHOT UTILITIES
-- =============================================================================

-- Capture selection area via grim/slurp, send output to swappy editor
hl.bind("Print", hl.dsp.exec_cmd(config.utils.screenshot), { locked = true })
hl.bind(config.mainMod .. " + P", hl.dsp.exec_cmd(config.utils.screenshot), { locked = true })

-- =============================================================================
-- WALLPAPER & CLIPBOARD HISTORY SCRIPTS
-- =============================================================================

-- Cycle desktop wallpaper using swww daemon script
hl.bind(config.mainMod .. " + ALT + Right", hl.dsp.exec_cmd(config.utils.wallpaper), { description = "Change wallpaper" })

-- Query and decode clipboard history via wofi selection and paste it to wl-copy
hl.bind(config.mainMod .. " + SHIFT + V", hl.dsp.exec_cmd(string.format(config.utils.clipboard, config.apps.menu)),
  { description = "Clipboard history" })

-- =============================================================================
-- WORKSPACE MANAGEMENT BINDINGS
-- =============================================================================

-- Move active window to a workspace SILENTLY (focus does not follow to destination workspace)
-- Mapped to number keys 1 through 9 using hardware keycodes
for i = 1, 9 do
  local numberkey = { 10, 11, 12, 13, 14, 15, 16, 17, 18, 19 }
  hl.bind(config.mainMod .. " + ALT + code:" .. numberkey[i], hl.dsp.window.move({ workspace = i, follow = false }))
end

-- Move active window to a workspace SILENTLY using hardware Numpad keycodes
for i = 1, 9 do
  local numpadkey = { 87, 88, 89, 83, 84, 85, 79, 80, 81, 90 }
  hl.bind(config.mainMod .. " + ALT + code:" .. numpadkey[i], hl.dsp.window.move({ workspace = i, follow = false }))
end

-- Relative navigation: Switch focus to adjacent workspace (Left or Right)
hl.bind("CTRL + SUPER + Right", hl.dsp.focus({ workspace = "r+1" }))
hl.bind("CTRL + SUPER + Left", hl.dsp.focus({ workspace = "r-1" }))

-- Absolute navigation: Focus workspaces 1 through 9
for i = 1, 9 do
  hl.bind(config.mainMod .. " + " .. i, hl.dsp.focus({ workspace = i }))
end

-- Move active window to workspace and FOLLOW focus to destination workspace (workspaces 1 to 9)
for i = 1, 9 do
  hl.bind(config.mainMod .. " + SHIFT + " .. i, hl.dsp.window.move({ workspace = i, follow = true }))
end

-- =============================================================================
-- INTERACTIVE MOUSE BINDINGS
-- =============================================================================

-- Drag floating windows with SUPER + Left Mouse Button
hl.bind(config.mainMod .. " + mouse:272", hl.dsp.window.drag(), { mouse = true, description = "Move window" })

-- Resize floating windows with SUPER + Right Mouse Button
hl.bind(config.mainMod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true, description = "Resize window" })
