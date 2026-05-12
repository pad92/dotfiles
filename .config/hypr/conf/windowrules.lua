-- Window Rules configuration

-- Polkit agents
hl.window_rule({ match = { class = "^(?i)(hyprpolkitagent|polkit-kde-authentication-agent-1|org.kde.polkit-kde-authentication-agent-1|polkit-gnome-authentication-agent-1|gcr-prompter|pinentry-.*)$" }, float = true, center = true, rounding = 12 })

-- Steam
hl.window_rule({ match = { class = "^(?i)(steam)$", title = "^(?i)(Friends List|.*Chat.*|Settings|.* - News|Screenshot)$" }, float = true, size = { 700, 750 }, rounding = 12 })
hl.window_rule({ match = { title = "^(?i)(Sign in to Steam)$" }, float = true, center = true })
hl.window_rule({ match = { class = "^(?i)(steam)$", title = "^(?i)(Steam Big Picture Mode)$" }, fullscreen = true, monitor = "desc:ASUSTek COMPUTER INC XG32WCS TALMAS012758" })
hl.window_rule({ match = { class = "^(?i)(gamescope|steam_app_.*)$" }, fullscreen = true, immediate = true, monitor = "desc:ASUSTek COMPUTER INC XG32WCS TALMAS012758" })

-- Other apps
hl.window_rule({ match = { class = "^(?i)(pavucontrol|org.pulseaudio.pavucontrol|pavucontrol-qt)$" }, float = true, size = { 900, 600 }, rounding = 12 })
hl.window_rule({ match = { class = "^(?i)(org.keepassxc.KeePassXC|Bitwarden|1Password)$" }, float = true, center = true })
hl.window_rule({ match = { class = "^(?i)(org.keepassxc.KeePassXC)$" }, size = { 900, 500 } })
hl.window_rule({ match = { class = "^(?i)(org.keepassxc.KeePassXC)$", title = "^(?i)(Unlock Database)$" }, float = true })
hl.window_rule({ match = { class = "^(?i)(Bitwarden)$" }, size = { 800, 600 } })

-- Simple rules
hl.window_rule({ match = { class = "^(Rofi)$", title = "^(rofi - dmenu)$" }, float = true })
hl.window_rule({ match = { class = "^(blueman-manager)$" }, float = true })
hl.window_rule({ match = { class = "^(codium)$", title = "^(Save Workspace)$" }, float = true })
hl.window_rule({ match = { class = "^(com.github.wwmm.easyeffects)$" }, float = true })
hl.window_rule({ match = { class = "^(firefox)$", title = "^(Library)$" }, float = true })
hl.window_rule({ match = { class = "^(kitty)$", title = "^(btop)$" }, float = true })
hl.window_rule({ match = { class = "^(kitty)$", title = "^(htop)$" }, float = true })
hl.window_rule({ match = { class = "^(kitty)$", title = "^(top)$" }, float = true })
hl.window_rule({ match = { class = "^(kvantummanager)$" }, float = true })
hl.window_rule({ match = { class = "^(nm-applet)$" }, float = true })
hl.window_rule({ match = { class = "^(nm-connection-editor)$" }, float = true })
hl.window_rule({ match = { class = "^(nwg-look)$" }, float = true })
hl.window_rule({ match = { class = "^(org.kde.ark)$" }, float = true })
hl.window_rule({ match = { class = "^(org.kde.dolphin)$", title = "^(Copying — Dolphin)$" }, float = true })
hl.window_rule({ match = { class = "^(org.kde.dolphin)$", title = "^(Progress Dialog — Dolphin)$" }, float = true })
hl.window_rule({ match = { class = "^(org.kde.polkit-kde-authentication-agent-1)$" }, float = true })
hl.window_rule({ match = { class = "^(qt5ct)$" }, float = true })
hl.window_rule({ match = { class = "^(qt6ct)$" }, float = true })
hl.window_rule({ match = { class = "^(vlc)$" }, float = true })
hl.window_rule({ match = { title = "^(About Mozilla Firefox)$" }, float = true })
hl.window_rule({ match = { title = "^(Picture-in-Picture)$" }, float = true })

hl.window_rule({ match = { class = "^(app.drey.Warp)$" }, float = true })
hl.window_rule({ match = { class = "^(com.github.rafostar.Clapper)$" }, float = true })
hl.window_rule({ match = { class = "^(com.github.unrud.VideoDownloader)$" }, float = true })
hl.window_rule({ match = { class = "^(eog)$" }, float = true })
hl.window_rule({ match = { class = "^(io.github.alainm23.planify)$" }, float = true })
hl.window_rule({ match = { class = "^(io.gitlab.adhami3310.Impression)$" }, float = true })
hl.window_rule({ match = { class = "^(io.gitlab.theevilskeleton.Upscaler)$" }, float = true })
hl.window_rule({ match = { class = "^(io.missioncenter.MissionCenter)$" }, float = true })
hl.window_rule({ match = { class = "^(net.davidotek.pupgui2)$" }, float = true })
hl.window_rule({ match = { class = "^(org.telegram.desktop)$" }, float = true })
hl.window_rule({ match = { class = "^(Plexamp)$" }, float = true })
hl.window_rule({ match = { class = "^(Signal)$" }, float = true })
hl.window_rule({ match = { class = "^(yad)$" }, float = true })

-- Layer rules
hl.layer_rule({ match = { namespace = "logout_dialog" }, blur = true })
hl.layer_rule({ match = { namespace = "notifications" }, blur = true, ignore_alpha = 0 })
hl.layer_rule({ match = { namespace = "rofi" }, blur = true, ignore_alpha = 0 })
hl.layer_rule({ match = { namespace = "swaync-control-center" }, blur = true, ignore_alpha = 0 })
hl.layer_rule({ match = { namespace = "swaync-notification-window" }, blur = true, ignore_alpha = 0 })
