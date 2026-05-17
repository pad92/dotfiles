-- =============================================================================
-- HYPRLAND AUTOSTART CONFIGURATION
-- =============================================================================
-- Executed once when Hyprland launches to setup themes, services, applets, and clipboard.

hl.on("hyprland.start", function()
  local config = require("config")

  -- 1. Environment & Theme settings
  -- Applies GTK/GNOME theme settings stored in config.lua via gsettings
  for _, setting in ipairs(config.theme_settings) do
    hl.exec_cmd("gsettings set " .. setting.key .. " " .. setting.value)
  end

  -- Set system-wide mouse cursor theme and size using hyprctl
  hl.exec_cmd("hyprctl setcursor Adwaita 24")

  -- 2. System Core & Environment Setup
  -- Import system environment variables into systemd and D-Bus user sessions
  hl.exec_cmd("systemctl --user import-environment")
  hl.exec_cmd("dbus-update-activation-environment --systemd")
  hl.exec_cmd("hash dbus-update-activation-environment 2>/dev/null")
  
  -- Launch Polkit authentication agent (checks common locations for polkit agent)
  hl.exec_cmd(
  "/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1 || /usr/libexec/polkit-gnome-authentication-agent-1")

  -- 3. Core Desktop Services & Applets
  -- Starts background components such as waybar, blueman, network indicators, etc.
  for _, app in ipairs(config.autostart_apps) do
    hl.exec_cmd(app)
  end

  -- 4. Clipboard History Management
  -- Uses cliphist to automatically track and cache copied text and images
  hl.exec_cmd("wl-paste --type text --watch cliphist store")
  hl.exec_cmd("wl-paste --type image --watch cliphist store")
end)
