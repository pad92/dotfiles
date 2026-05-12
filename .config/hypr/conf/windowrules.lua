-- Window Rules configuration

-- Polkit agents
hl.windowrule({
    name = "polkit-agents",
    match_class = "^(?i)(hyprpolkitagent|polkit-kde-authentication-agent-1|org.kde.polkit-kde-authentication-agent-1|polkit-gnome-authentication-agent-1|gcr-prompter|pinentry-.*)$",
    float = true,
    center = true,
    rounding = 12,
})

-- Steam
hl.windowrule({
    name = "steam-float",
    match_class = "^(?i)(steam)$",
    match_title = "^(?i)(Friends List|.*Chat.*|Settings|.* - News|Screenshot)$",
    float = true,
    size = "700 750",
    rounding = 12,
})

hl.windowrule({
    name = "steam-signin",
    match_title = "^(?i)(Sign in to Steam)$",
    float = true,
    center = true,
})

hl.windowrule({
    name = "steam-no-center",
    match_class = "^(?i)(steam)$",
    center = false,
})

hl.windowrule({
    name = "steam-bigpicture",
    match_class = "^(?i)(steam)$",
    match_title = "^(?i)(Steam Big Picture Mode)$",
    fullscreen = true,
    monitor = "desc:ASUSTek COMPUTER INC XG32WCS TALMAS012758",
})

hl.windowrule({
    name = "steam-games",
    match_class = "^(?i)(gamescope|steam_app_.*)$",
    fullscreen = true,
    monitor = "desc:ASUSTek COMPUTER INC XG32WCS TALMAS012758",
    immediate = true,
})

-- Other apps
hl.windowrule({
    name = "pavucontrol",
    match_class = "^(?i)(pavucontrol|org.pulseaudio.pavucontrol|pavucontrol-qt)$",
    float = true,
    size = "900 600",
    rounding = 12,
})

hl.windowrule({
    name = "password-managers",
    match_class = "^(?i)(org.keepassxc.KeePassXC|Bitwarden|1Password)$",
    float = true,
    center = true,
})

hl.windowrule({
    name = "keepassxc",
    match_class = "^(?i)(org.keepassxc.KeePassXC)$",
    size = "900 500",
})

hl.windowrule({
    name = "keepassxc-unlock",
    match_class = "^(?i)(org.keepassxc.KeePassXC)$",
    match_title = "^(?i)(Unlock Database)$",
    float = true,
})

hl.windowrule({
    name = "bitwarden",
    match_class = "^(?i)(Bitwarden)$",
    size = "800 600",
})

-- Simple rules
hl.windowrule("float", "match:class ^(Rofi)$, match:title ^(rofi - dmenu)$")
hl.windowrule("float", "match:class ^(blueman-manager)$")
hl.windowrule("float", "match:class ^(codium)$, match:title ^(Save Workspace)$")
hl.windowrule("float", "match:class ^(com.github.wwmm.easyeffects)$")
hl.windowrule("float", "match:class ^(firefox)$, match:title ^(Library)$")
hl.windowrule("float", "match:class ^(kitty)$, match:title ^(btop)$")
hl.windowrule("float", "match:class ^(kitty)$, match:title ^(htop)$")
hl.windowrule("float", "match:class ^(kitty)$, match:title ^(top)$")
hl.windowrule("float", "match:class ^(kvantummanager)$")
hl.windowrule("float", "match:class ^(nm-applet)$")
hl.windowrule("float", "match:class ^(nm-connection-editor)$")
hl.windowrule("float", "match:class ^(nwg-look)$")
hl.windowrule("float", "match:class ^(org.kde.ark)$")
hl.windowrule("float", "match:class ^(org.kde.dolphin)$, match:title ^(Copying — Dolphin)$")
hl.windowrule("float", "match:class ^(org.kde.dolphin)$, match:title ^(Progress Dialog — Dolphin)$")
hl.windowrule("float", "match:class ^(org.kde.polkit-kde-authentication-agent-1)$")
hl.windowrule("float", "match:class ^(qt5ct)$")
hl.windowrule("float", "match:class ^(qt6ct)$")
hl.windowrule("float", "match:class ^(vlc)$")
hl.windowrule("float", "match:title ^(About Mozilla Firefox)$")
hl.windowrule("float", "match:title ^(Picture-in-Picture)$")

hl.windowrule("float", "match:class ^(app.drey.Warp)$")
hl.windowrule("float", "match:class ^(com.github.rafostar.Clapper)$")
hl.windowrule("float", "match:class ^(com.github.unrud.VideoDownloader)$")
hl.windowrule("float", "match:class ^(eog)$")
hl.windowrule("float", "match:class ^(io.github.alainm23.planify)$")
hl.windowrule("float", "match:class ^(io.gitlab.adhami3310.Impression)$")
hl.windowrule("float", "match:class ^(io.gitlab.theevilskeleton.Upscaler)$")
hl.windowrule("float", "match:class ^(io.missioncenter.MissionCenter)$")
hl.windowrule("float", "match:class ^(net.davidotek.pupgui2)$")
hl.windowrule("float", "match:class ^(org.telegram.desktop)$")
hl.windowrule("float", "match:class ^(Plexamp)$")
hl.windowrule("float", "match:class ^(Signal)$")
hl.windowrule("float", "match:class ^(yad)$")

-- Layer rules
hl.layerrule("blur", "match:namespace logout_dialog")
hl.layerrule("blur", "match:namespace notifications", { ignore_alpha = 0 })
hl.layerrule("blur", "match:namespace rofi", { ignore_alpha = 0 })
hl.layerrule("blur", "match:namespace swaync-control-center", { ignore_alpha = 0 })
hl.layerrule("blur", "match:namespace swaync-notification-window", { ignore_alpha = 0 })
