-- █▄░█ █░█ █ █▀▄ █ ▄▀█
-- █░▀█ ▀▄▀ █ █▄▀ █ █▀█

-- Intel graphics optimization for reduced CPU and GPU usage
-- See https://wiki.hyprland.org/Intel-Graphics/

-- Intel graphics environment variables for power saving
hl.env("__GLX_VENDOR_LIBRARY_NAME", "intel")
hl.env("__VK_LAYER_NV_optimus", "INTEL_only")
hl.env("DRI_PRIME", "0")
hl.env("GBM_BACKEND", "drm")
hl.env("LIBVA_DRIVER_NAME", "iHD")
hl.env("WLR_DRM_NO_ATOMIC", "1")

-- Disable NVIDIA offloading to reduce power consumption
-- hl.env("__NV_PRIME_RENDER_OFFLOAD", "1")

-- Intel-specific optimizations
hl.env("INTEL_DRIVER", "1")
hl.env("mesa_glthread", "true")
hl.env("MESA_LOADER_DRIVER_OVERRIDE", "iris")

-- Additional Intel-specific environment variables for power management
hl.env("VblankMode", "0")
hl.env("MESA_GLSL_CACHE_DISABLE", "1")
