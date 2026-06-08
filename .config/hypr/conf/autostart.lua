-- =============================================================================
-- HYPRLAND AUTOSTART CONFIGURATION
-- =============================================================================
-- Executed once when Hyprland launches to setup themes, services, applets, and clipboard.

hl.on("hyprland.start", function()
  local config = require("config")
  local utils = require("include.utils")

  -- 1. Environment & Theme settings
  -- Applies GTK/GNOME theme settings stored in config.lua via gsettings
  for _, setting in ipairs(config.theme) do
    hl.exec_cmd("gsettings set " .. setting.key .. " " .. setting.value)
  end

  -- Set system-wide mouse cursor theme and size using hyprctl
  hl.exec_cmd("hyprctl setcursor " .. config.visuals.cursor_theme .. " " .. tostring(config.visuals.cursor_size))

  -- 2. System Core & Authentication Setup
  -- Launch Polkit authentication agent via UWSM 
  hl.exec_cmd("uwsm app -- /usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1 || uwsm app -- /usr/libexec/polkit-gnome-authentication-agent-1")

  -- 3. Core Desktop Services & Applets
  -- Starts background components such as waybar, blueman, network indicators, etc.
  for _, app in ipairs(config.autostart) do
    utils.uwsm_app(app)
  end

  -- 4. Clipboard History Management
  -- Uses cliphist to automatically track and cache copied text and images
  utils.uwsm_app("wl-paste --type text --watch cliphist store")
  utils.uwsm_app("wl-paste --type image --watch cliphist store")
end)