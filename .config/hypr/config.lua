local uwsm = "uwsm app -- "

local config = {
    -- =============================================================================
    -- GENERAL
    -- =============================================================================
    mainMod = "SUPER",

    -- =============================================================================
    -- APPLICATION DEFAULTS
    -- =============================================================================
    apps = {
        term             = uwsm .. (os.getenv("TERMINAL") or "alacritty"),
        editor           = uwsm .. "vscodium",
        file             = uwsm .. "nautilus",
        browser          = uwsm .. (os.getenv("BROWSER") or "firefox"),
        music            = uwsm .. "spotify-launcher",
        password_manager = uwsm .. "proton-pass",
        menu             = "wofi -s ~/.config/wofi/menu.css",
    },

    -- =============================================================================
    -- INTERFACE & VISUALS
    -- =============================================================================
    visuals = {
        gaps_in          = 2,
        gaps_out         = 2,
        rounding         = 10,
        rounding_power   = 2.5,
        border_size      = 2,
        font             = "JetBrainsMono Nerd Font",
        font_size        = 12,
        cursor_theme     = os.getenv("XCURSOR_THEME") or "Adwaita",
        cursor_size      = tonumber(os.getenv("XCURSOR_SIZE")) or 24,

        blur = {
            enabled = true,
            size = 6,
            passes = 2,
            new_optimizations = true,
            ignore_opacity = true,
            xray = true
        },
        shadow = {
            enabled = true,
            range = 20,
            offset = {0, 2},
            render_power = 10
        }
    },

    -- =============================================================================
    -- LAYOUT CONFIGURATIONS
    -- =============================================================================
    layout = {
        active_layout = "dwindle",
        resize_on_border = true,
        dwindle = {
            preserve_split = true,
            smart_split = false,
            smart_resizing = false,
        }
    },

    -- =============================================================================
    -- INPUT SETTINGS (KEYBOARD, MOUSE, TOUCHPAD, GESTURES)
    -- =============================================================================
    input = {
        kb_layout          = "us",
        kb_variant         = "intl",
        follow_mouse       = 1,
        numlock_by_default = true,
        sensitivity        = 0,

        touchpad = {
            natural_scroll       = false,
            tap_to_click         = true,
            disable_while_typing = true,
            scroll_factor        = 0.5,
            tap_and_drag         = true,
            drag_lock            = false,
        },
        cursor = {
            no_hardware_cursors = false,
            enable_hyprcursor   = true,
        },
        gestures = {
            workspace_swipe_distance           = 500,
            workspace_swipe_invert             = true,
            workspace_swipe_min_speed_to_force = 30,
            workspace_swipe_cancel_ratio       = 0.5,
            workspace_swipe_create_new         = true,
            workspace_swipe_forever            = true,
        },
        device_overrides = {
            name        = "epic mouse V1",
            sensitivity = -0.5,
        }
    },

    -- =============================================================================
    -- COLORS (GRUVBOX HARMONIOUS ACCENTS)
    -- =============================================================================
    colors = {
        accent           = "#83a598",   -- bright_blue
        background       = "#1d2021",   -- bg
        foreground       = "#ebdbb2",   -- light1
        active_border    = "#83a598cc", -- bright_blue
        inactive_border  = "#928374cc", -- gray
        shadow           = "#1d202120", -- bg
    },

    -- =============================================================================
    -- SYSTEM UTILITIES, AUTHENTICATION & COMMANDS
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
    },

    -- =============================================================================
    -- GTK & THEME SETTINGS (GSETTINGS OVERRIDES)
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
