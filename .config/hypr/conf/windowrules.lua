-- Polkit authentication agents
hl.window_rule({ match = { class = "^(?i)(hyprpolkitagent|polkit-kde-authentication-agent-1|org.kde.polkit-kde-authentication-agent-1|polkit-gnome-authentication-agent-1|gcr-prompter|pinentry-.*)$" }, float = true, center = true, rounding = 12 })

-- Steam
hl.window_rule({ match = { class = "^(?i)(steam)$", title = "^(?i)(Friends List|.*Chat.*|Settings|.* - News|Screenshot)$" }, float = true, size = { 700, 750 }, rounding = 12 })
hl.window_rule({ match = { title = "^(?i)(Sign in to Steam)$" }, float = true, center = true })
hl.window_rule({ match = { class = "^(?i)(steam)$", title = "^(?i)(Steam Big Picture Mode)$" }, fullscreen = true })
hl.window_rule({ match = { class = "^(?i)(gamescope|steam_app_.*)$" }, fullscreen = true, immediate = true, confine_pointer = 1 })

-- Audio & password manager
hl.window_rule({ match = { class = "^(?i)(pavucontrol|org.pulseaudio.pavucontrol|pavucontrol-qt)$" }, float = true, size = { 900, 600 }, rounding = 12 })
hl.window_rule({ match = { class = "^(?i)(Proton Pass)$" }, float = true, center = true })

-- Floating applications
local float_apps = {
  "blueman-manager", "com.github.wwmm.easyeffects", "kvantummanager",
  "nm-applet", "nm-connection-editor", "nwg-look", "org.kde.ark", "qt5ct", "qt6ct",
  "vlc", "app.drey.Warp", "com.github.rafostar.Clapper", "com.github.unrud.VideoDownloader",
  "eog", "io.github.alainm23.planify", "io.gitlab.adhami3310.Impression",
  "io.gitlab.theevilskeleton.Upscaler", "io.missioncenter.MissionCenter",
  "net.davidotek.pupgui2", "org.telegram.desktop", "Plexamp", "Signal", "yad"
}
for _, class in ipairs(float_apps) do
  hl.window_rule({ match = { class = "^(" .. class .. ")$" }, float = true })
end

-- Dialog overrides
hl.window_rule({ match = { class = "^(codium)$", title = "^(Save Workspace)$" }, float = true })
hl.window_rule({ match = { class = "^(firefox)$", title = "^(Library)$" }, float = true })
hl.window_rule({ match = { title = "^(About Mozilla Firefox|Picture-in-Picture)$" }, float = true })

-- Layer blur
hl.layer_rule({ match = { namespace = "logout_dialog" }, blur = true, ignore_alpha = 0 })
