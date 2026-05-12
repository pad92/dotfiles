-- Autostart configuration
hl.on("hyprland.start", function()
  -- 1. Environment & Theme settings
  local theme_settings = {
    { key = "org.gnome.desktop.interface icon-theme",          value = "'Papirus-Dark'" },
    { key = "org.gnome.desktop.interface gtk-theme",           value = "'Materia-dark-compact'" },
    { key = "org.gnome.desktop.interface color-scheme",        value = "'prefer-dark'" },
    { key = "org.gnome.desktop.interface cursor-theme",        value = "'Adwaita'" },
    { key = "org.gnome.desktop.interface cursor-size",         value = "24" },
    { key = "org.gnome.desktop.interface font-antialiasing",   value = "'rgba'" },
    { key = "org.gnome.desktop.interface font-hinting",        value = "'full'" },
    { key = "org.gnome.desktop.interface monospace-font-name", value = "'SauceCodePro Nerd Font 14'" },
    { key = "org.gnome.desktop.interface font-name",           value = "'Cantarell 10'" },
    { key = "org.gnome.desktop.interface document-font-name",  value = "'Cantarell 10'" },
  }

  for _, setting in ipairs(theme_settings) do
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
  local apps = {
    "waybar",
    "blueman-applet",
    "nm-applet --indicator",
    "/usr/bin/swayosd-server",
    "1password --silent",
  }

  for _, app in ipairs(apps) do
    hl.exec_cmd(app)
  end

  -- 4. Clipboard management
  hl.exec_cmd("wl-paste --type text --watch cliphist store")
  hl.exec_cmd("wl-paste --type image --watch cliphist store")
end)
