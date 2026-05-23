local config = {
    -- =============================================================================
    -- GENERAL
    -- =============================================================================
    mainMod = "SUPER",

    -- =============================================================================
    -- APPLICATION DEFAULTS
    -- =============================================================================
    apps = {
        term             = "alacritty",
        editor           = "vscodium",
        file             = "nautilus",
        browser          = "firefox",
        music            = "spotify-launcher",
        password_manager = "1Password",
        menu             = "wofi -s ~/.config/wofi/menu.css",
    },

    -- =============================================================================
    -- INTERFACE & VISUALS
    -- =============================================================================
    visuals = {
        gaps_in          = 2,
        gaps_out         = 2,
        rounding         = 10,
        border_size      = 2,
        font             = "JetBrainsMono Nerd Font",
        font_size        = 12,
    },

    -- =============================================================================
    -- INPUT SETTINGS
    -- =============================================================================
    input = {
        kb_layout = "us",
        kb_variant = "intl",
    },

    -- =============================================================================
    -- COLORS
    -- =============================================================================
    colors = {
        accent           = "#89b4fa",
        background       = "#1e1e2e",
        foreground       = "#cdd6f4",
        active_border    = "#b4befecc",
        inactive_border  = "#9399b2cc",
        shadow           = "#1e1e2e20",
    },

    -- =============================================================================
    -- SYSTEM UTILITIES & COMMANDS
    -- =============================================================================
    utils = {
        screenshot = "grim -g \"$(slurp -d)\" - | swappy -f -",
        lock       = "hyprlock -c ~/.config/hypr/hyprlock.conf",
        logout     = "qs -c $qsConfig ipc call TEST_ALIVE || pkill wlogout || wlogout -p layer-shell",
        vol_mute   = "swayosd-client --output-volume mute-toggle",
        mic_mute   = "swayosd-client --input-volume mute-toggle",
        vol_up     = "swayosd-client --output-volume raise",
        vol_down   = "swayosd-client --output-volume lower",
        media_play_pause = "playerctl play-pause",
        media_next = "playerctl next",
        media_prev = "playerctl previous",
        bright_up  = "swayosd-client --brightness raise",
        bright_down = "swayosd-client --brightness lower",
        caps_lock  = "swayosd-client --caps-lock",
        wallpaper  = "~/.dotfiles/bin/awww.sh",
        clipboard  = "cliphist list | %s -S dmenu | cliphist decode | wl-copy",
    },

    -- =============================================================================
    -- NOTIFICATIONS
    -- =============================================================================
    notifications = {
        duration   = 3000,
        font_size  = 12,
    },

    -- =============================================================================
    -- AUTOSTART APPLICATIONS
    -- =============================================================================
    autostart = {
        "blueman-applet",
        "nm-applet --indicator",
        "/usr/bin/swayosd-server",
        "1password --silent",
    },

    -- =============================================================================
    -- GTK & THEME SETTINGS
    -- =============================================================================
    theme = {
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
