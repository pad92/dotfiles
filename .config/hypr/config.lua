local tk = require("include.toolkit").load()

local uwsm = "uwsm app -- "
local font_name = tk.font_family or "DejaVu Sans"
local font_size = tk.font_size or 10
local cursor_theme = os.getenv("XCURSOR_THEME") or "Adwaita"
local cursor_size = tonumber(os.getenv("XCURSOR_SIZE")) or 24

local config = {
  -- =============================================================================
  -- GENERAL
  -- =============================================================================
  mainMod = "SUPER",

  -- =============================================================================
  -- APPLICATION DEFAULTS
  -- =============================================================================
  apps = {
    term = uwsm .. (os.getenv("TERMINAL") or "alacritty"),
    editor = uwsm .. "vscodium",
    file = uwsm .. "nautilus",
    browser = uwsm .. (os.getenv("BROWSER") or "firefox"),
    music = uwsm .. "spotify-launcher",
    password_manager = uwsm .. "proton-pass",
    menu = "hyprlauncher",
  },

  -- =============================================================================
  -- INTERFACE & VISUALS
  -- =============================================================================
  visuals = {
    gaps_in = 2,
    gaps_out = 2,
    rounding = tk.rounding_large or 10,
    rounding_power = 2.5,
    border_size = 2,
    font = font_name,
    font_size = font_size + 2,
    cursor_theme = cursor_theme,
    cursor_size = cursor_size,

    blur = {
      enabled = true,
      size = 6,
      passes = 2,
      new_optimizations = true,
      ignore_opacity = true,
      xray = true,
    },
    shadow = {
      enabled = true,
      range = 20,
      offset = { 0, 2 },
      render_power = 10,
    },
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
    },
  },

  -- =============================================================================
  -- INPUT SETTINGS (KEYBOARD, MOUSE, TOUCHPAD, GESTURES)
  -- =============================================================================
  input = {
    kb_layout = "us",
    kb_variant = "intl",
    follow_mouse = 1,
    numlock_by_default = true,
    sensitivity = 0,

    touchpad = {
      natural_scroll = false,
      tap_to_click = true,
      disable_while_typing = true,
      scroll_factor = 0.5,
      tap_and_drag = true,
      drag_lock = false,
    },
    cursor = {
      no_hardware_cursors = false,
      enable_hyprcursor = true,
    },
    gestures = {
      workspace_swipe_distance = 500,
      workspace_swipe_invert = true,
      workspace_swipe_min_speed_to_force = 30,
      workspace_swipe_cancel_ratio = 0.5,
      workspace_swipe_create_new = true,
      workspace_swipe_forever = true,
    },
    device_overrides = {
      name = "epic mouse V1",
      sensitivity = -0.5,
    },
  },

  -- =============================================================================
  -- COLORS (GRUVBOX HARMONIOUS ACCENTS)
  -- =============================================================================
  colors = {
    accent = tk.accent or "#83a598", -- bright_blue
    background = tk.background or "#1d2021", -- bg
    foreground = tk.text or "#ebdbb2", -- light1
    active_border = tk.accent and (tk.accent .. "cc") or "#83a598cc", -- bright_blue
    inactive_border = tk.alternate_base and (tk.alternate_base .. "cc") or "#928374cc", -- gray
    shadow = tk.background and (tk.background .. "20") or "#1d202120", -- bg
  },

  -- =============================================================================
  -- SYSTEM UTILITIES, AUTHENTICATION & COMMANDS
  -- =============================================================================
  utils = {
    screenshot = 'grim -g "$(slurp -d)" - | swappy -f -',
    lock = "hyprlock -c ~/.config/hypr/hyprlock.conf",
    logout = "qs -c $qsConfig ipc call TEST_ALIVE || pkill wlogout || wlogout -p layer-shell",
    vol_mute = "swayosd-client --output-volume mute-toggle",
    mic_mute = "swayosd-client --input-volume mute-toggle",
    vol_up = "swayosd-client --output-volume raise",
    vol_down = "swayosd-client --output-volume lower",
    media_play_pause = "playerctl play-pause",
    media_next = "playerctl next",
    media_prev = "playerctl previous",
    bright_up = "swayosd-client --brightness raise",
    bright_down = "swayosd-client --brightness lower",
    caps_lock = "swayosd-client --caps-lock",
    wallpaper = "~/.dotfiles/bin/awww.sh",
    clipboard = "cliphist list | %s -m | cliphist decode | wl-copy",
  },

  -- =============================================================================
  -- NOTIFICATIONS
  -- =============================================================================
  notifications = {
    duration = 3000,
    font_size = font_size + 2,
  },

  -- =============================================================================
  -- AUTOSTART APPLICATIONS
  -- =============================================================================
  autostart = {
    "blueman-applet",
    "nm-applet --indicator",
    "/usr/bin/swayosd-server",
    "hyprlauncher -d",
  },

  -- =============================================================================
  -- GTK & THEME SETTINGS (GSETTINGS OVERRIDES)
  -- =============================================================================
  theme = {
    { key = "org.gnome.desktop.interface icon-theme", value = "'Papirus-Dark'" },
    { key = "org.gnome.desktop.interface gtk-theme", value = "'Materia-dark-compact'" },
    { key = "org.gnome.desktop.interface color-scheme", value = "'prefer-dark'" },
    { key = "org.gnome.desktop.interface cursor-theme", value = "'" .. cursor_theme .. "'" },
    { key = "org.gnome.desktop.interface cursor-size", value = tostring(cursor_size) },
    { key = "org.gnome.desktop.interface font-antialiasing", value = "'rgba'" },
    { key = "org.gnome.desktop.interface font-hinting", value = "'full'" },
    { key = "org.gnome.desktop.interface monospace-font-name", value = "'JetBrainsMono Nerd Font 10'" },
    { key = "org.gnome.desktop.interface font-name", value = "'" .. font_name .. " " .. font_size .. "'" },
    { key = "org.gnome.desktop.interface document-font-name", value = "'" .. font_name .. " " .. font_size .. "'" },
  },
}

return config
