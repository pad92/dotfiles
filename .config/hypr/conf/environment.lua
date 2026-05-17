-- =============================================================================
-- SYSTEM ENVIRONMENT VARIABLES
-- =============================================================================
-- Configures core session paths, hardware/rendering properties, scale, and toolkits.

-- Desktop Environment Identity (essential for portal operations)
hl.env("XDG_CURRENT_DESKTOP", "Hyprland")
hl.env("XDG_SESSION_TYPE", "wayland")
hl.env("XDG_SESSION_DESKTOP", "Hyprland")

-- Force Firefox to run natively on Wayland
hl.env("MOZ_ENABLE_WAYLAND", "1")

-- UI Toolkit Rendering Backends (prefer Wayland native, fallback to X11)
hl.env("GDK_BACKEND", "wayland,x11")
hl.env("CLUTTER_BACKEND", "wayland")

-- Screen and Mouse Cursor Properties
hl.env("GDK_SCALE", "1")
hl.env("WLR_NO_HARDWARE_CURSORS", "1") -- Needed for compatibility on some graphics drivers
hl.env("HYPRCURSOR_SIZE", "24")
hl.env("XCURSOR_SIZE", "24")
hl.env("QT_CURSOR_SIZE", "24")

-- Force Electron-based apps (VSCode, Discord, Slack, etc.) to use Wayland
hl.env("ELECTRON_OZONE_PLATFORM_HINT", "auto")

-- QT Toolkit Wayland configuration & appearance
hl.env("QT_QPA_PLATFORM", "wayland;xcb")
hl.env("QT_QPA_PLATFORMTHEME", "qt6ct")                 -- Controls styles/themes of Qt apps using qt6ct
hl.env("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
hl.env("QT_WAYLAND_DISABLE_WINDOWDECORATION", "1")     -- Prevents Qt apps from drawing duplicate window headers
