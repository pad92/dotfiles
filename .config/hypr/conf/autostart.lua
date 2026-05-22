-- =============================================================================
-- HYPRLAND AUTOSTART CONFIGURATION
-- =============================================================================
-- Executed once when Hyprland launches to setup themes, services, applets, and clipboard.

hl.on("hyprland.start", function()
  local config = require("config")

  -- Helper to launch apps via UWSM
  local function uwsm_app(cmd)
    hl.exec_cmd("uwsm app -- " .. cmd)
  end

  -- 1. Environment & Theme settings
  -- Applies GTK/GNOME theme settings stored in config.lua via gsettings
  for _, setting in ipairs(config.theme) do
    hl.exec_cmd("gsettings set " .. setting.key .. " " .. setting.value)
  end

  -- Set system-wide mouse cursor theme and size using hyprctl
  hl.exec_cmd("hyprctl setcursor Adwaita 24")

  -- 2. System Core & Environment Setup
  -- Import system environment variables into systemd and D-Bus user sessions
  local system_core = {
    "systemctl --user import-environment",
    "dbus-update-activation-environment --systemd",
    "hash dbus-update-activation-environment 2>/dev/null",
  }
  for _, cmd in ipairs(system_core) do
    hl.exec_cmd(cmd)
  end

  -- Launch Polkit authentication agent (checks common locations for polkit agent)
  hl.exec_cmd("uwsm app -- /usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1 || uwsm app -- /usr/libexec/polkit-gnome-authentication-agent-1")

  -- 3. Core Desktop Services & Applets
  -- Starts background components such as waybar, blueman, network indicators, etc.
  for _, app in ipairs(config.autostart) do
    uwsm_app(app)
  end

  -- 4. Clipboard History Management
  -- Uses cliphist to automatically track and cache copied text and images
  uwsm_app("wl-paste --type text --watch cliphist store")
  uwsm_app("wl-paste --type image --watch cliphist store")
end)
