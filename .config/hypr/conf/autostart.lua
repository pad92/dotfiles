hl.on("hyprland.start", function()
  local config = require("config")

  for _, setting in ipairs(config.theme) do
    hl.exec_cmd("gsettings set " .. setting.key .. " " .. setting.value)
  end

  hl.exec_cmd("hyprctl setcursor " .. config.visuals.cursor_theme .. " " .. tostring(config.visuals.cursor_size))
  hl.exec_cmd("uwsm app -- /usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1 || uwsm app -- /usr/libexec/polkit-gnome-authentication-agent-1")

  for _, app in ipairs(config.autostart) do
    hl.exec_cmd("uwsm app -- " .. app)
  end

  hl.exec_cmd("uwsm app -- wl-paste --type text --watch cliphist store")
  hl.exec_cmd("uwsm app -- wl-paste --type image --watch cliphist store")
end)
