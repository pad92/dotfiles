local config = {
    -- General Variables
    mainMod = "SUPER",
    term = "alacritty",
    editor = "vscodium",
    file = "nautilus",
    browser = "firefox",
    music = "spotify-launcher",
    password_manager = "1Password",
    menu = "wofi -s ~/.config/wofi/menu.css",

    -- Interface
    gaps_in = 2,
    gaps_out = 2,
    rounding = 10,
    border_size = 2,
    font = "JetBrainsMono Nerd Font",
    font_size = 12,

    -- Colors
    accent = "#89b4fa",
    background = "#1e1e2e",
    foreground = "#cdd6f4",
    border = "#585b70",
    active_border = "#b4befecc",
    inactive_border = "#6c7086cc",
    shadow = "#1e1e2e20",

    -- Notifications
    notif_duration = 3000,
    notif_font_size = 12,

    -- Autostart Applications
    autostart_apps = {
        "blueman-applet",
        "nm-applet --indicator",
        "/usr/bin/swayosd-server",
        "1password --silent",
    },

    -- Theme Settings
    theme_settings = {
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
    },
}

return config
