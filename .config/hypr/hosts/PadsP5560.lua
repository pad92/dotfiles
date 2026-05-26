-- █▄░█ █░█ █ █▀▄ █ ▄▀█
-- █░▀█ ▀▄▀ █ █▄▀ █ █▀█

-- Configuration du backend graphique pour l'iGPU Intel (TigerLake)
hl.env("GBM_BACKEND", "drm")
hl.env("LIBVA_DRIVER_NAME", "iHD")
hl.env("__GLX_VENDOR_LIBRARY_NAME", "mesa")

-- Isolation stricte du driver Vulkan sur Intel pour stopper les coredumps d'Electron
hl.env("VK_DRIVER_FILES", "/usr/share/vulkan/icd.d/intel_icd.json")

-- Session Wayland standard et intégration des toolkits
hl.env("XDG_SESSION_TYPE", "wayland")
hl.env("XDG_CURRENT_DESKTOP", "Hyprland")
hl.env("GDK_BACKEND", "wayland,x11,*")
hl.env("QT_QPA_PLATFORM", "wayland;xcb")
hl.env("ELECTRON_OZONE_PLATFORM_HINT", "auto")
