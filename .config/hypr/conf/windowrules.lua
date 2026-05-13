-- Window Rules configuration

-- Helper for simple floating windows
local function set_float(classes)
  if type(classes) == "string" then classes = { classes } end
  for _, class in ipairs(classes) do
    hl.window_rule({ match = { class = "^(" .. class .. ")$" }, float = true })
  end
end

-- Polkit agents
hl.window_rule({ match = { class = "^(?i)(hyprpolkitagent|polkit-kde-authentication-agent-1|org.kde.polkit-kde-authentication-agent-1|polkit-gnome-authentication-agent-1|gcr-prompter|pinentry-.*)$" }, float = true, center = true, rounding = 12 })

-- Steam
hl.window_rule({ match = { class = "^(?i)(steam)$", title = "^(?i)(Friends List|.*Chat.*|Settings|.* - News|Screenshot)$" }, float = true, size = { 700, 750 }, rounding = 12 })
hl.window_rule({ match = { title = "^(?i)(Sign in to Steam)$" }, float = true, center = true })
hl.window_rule({
  match = { class = "^(?i)(steam)$", title = "^(?i)(Steam Big Picture Mode)$" },
  fullscreen = true,
  monitor =
  "desc:ASUSTek COMPUTER INC XG32WCS TALMAS012758"
})
hl.window_rule({
  match = { class = "^(?i)(gamescope|steam_app_.*)$" },
  fullscreen = true,
  immediate = true,
  monitor =
  "desc:ASUSTek COMPUTER INC XG32WCS TALMAS012758"
})

-- Other apps (Specific sizes/centers)
hl.window_rule({ match = { class = "^(?i)(pavucontrol|org.pulseaudio.pavucontrol|pavucontrol-qt)$" }, float = true, size = { 900, 600 }, rounding = 12 })
hl.window_rule({ match = { class = "^(?i)(org.keepassxc.KeePassXC|Bitwarden|1Password)$" }, float = true, center = true })
hl.window_rule({ match = { class = "^(?i)(org.keepassxc.KeePassXC)$" }, size = { 900, 500 } })
hl.window_rule({ match = { class = "^(?i)(org.keepassxc.KeePassXC)$", title = "^(?i)(Unlock Database)$" }, float = true })
hl.window_rule({ match = { class = "^(?i)(Bitwarden)$" }, size = { 800, 600 } })

-- Simple floating rules
local float_apps = {
  "Rofi", "blueman-manager", "com.github.wwmm.easyeffects", "kvantummanager",
  "nm-applet", "nm-connection-editor", "nwg-look", "org.kde.ark", "qt5ct", "qt6ct",
  "vlc", "app.drey.Warp", "com.github.rafostar.Clapper", "com.github.unrud.VideoDownloader",
  "eog", "io.github.alainm23.planify", "io.gitlab.adhami3310.Impression",
  "io.gitlab.theevilskeleton.Upscaler", "io.missioncenter.MissionCenter",
  "net.davidotek.pupgui2", "org.telegram.desktop", "Plexamp", "Signal", "yad"
}
set_float(float_apps)

-- Special case rules (Title match)
hl.window_rule({ match = { class = "^(codium)$", title = "^(Save Workspace)$" }, float = true })
hl.window_rule({ match = { class = "^(firefox)$", title = "^(Library)$" }, float = true })
hl.window_rule({ match = { class = "^(kitty)$", title = "^(btop|htop|top)$" }, float = true })
hl.window_rule({ match = { class = "^(org.kde.dolphin)$", title = "^(Copying — Dolphin|Progress Dialog — Dolphin)$" }, float = true })
hl.window_rule({ match = { title = "^(About Mozilla Firefox|Picture-in-Picture)$" }, float = true })

-- Layer rules
local blur_layers = {
  "logout_dialog", "notifications", "rofi",
  "swaync-control-center", "swaync-notification-window"
}
for _, ns in ipairs(blur_layers) do
  hl.layer_rule({ match = { namespace = ns }, blur = true, ignore_alpha = 0 })
end
