-- Autostart configuration
hl.on("hyprland.start", function()
  local config = require("config")

  -- 1. Environment & Theme settings
  for _, setting in ipairs(config.theme_settings) do
    hl.exec_cmd("gsettings set " .. setting.key .. " " .. setting.value)
  end

  -- Cursor specific (hyprctl)
  hl.exec_cmd("hyprctl setcursor Adwaita 24")

  -- 2. System Core & Environment
  hl.exec_cmd("systemctl --user import-environment")
  hl.exec_cmd("dbus-update-activation-environment --systemd")
  hl.exec_cmd("hash dbus-update-activation-environment 2>/dev/null")
  hl.exec_cmd(
  "/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1 || /usr/libexec/polkit-gnome-authentication-agent-1")

  -- 3. Applications & Applets
  for _, app in ipairs(config.autostart_apps) do
    hl.exec_cmd(app)
  end

  -- 4. Clipboard management
  hl.exec_cmd("wl-paste --type text --watch cliphist store")
  hl.exec_cmd("wl-paste --type image --watch cliphist store")
end)
