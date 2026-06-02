-- =============================================================================
-- HOST-SPECIFIC CONFIGURATION: PadsP5560
-- =============================================================================
-- Configures hardware display monitors and custom window routing rules for this host.

-- 1. Hardware Monitor Display Layout
local monitors = {
  -- Primary/Left Monitor (Top row)
  {
    output = "desc:Dell Inc. DELL P2423DE 3PJ4CN3",
    mode = "2560x1440",
    position = "0x0",
    scale = 1
  },
  -- Laptop/Bottom-Left High-DPI Monitor
  {
    output = "desc:Sharp Corporation 0x1516",
    mode = "3840x2400",
    position = "0x1440",                    -- Placed directly below the Dell monitor
    scale = 2                                 -- UI scaling factor for High-DPI rendering
  },
  -- Secondary/Right Gaming Monitor (Top row)
  {
    output = "desc:ASUSTek COMPUTER INC XG32WCS TALMAS012758",
    mode = "2560x1440@144",
    position = "2560x0",                     -- Placed to the right of the Dell monitor
    scale = 1,
    bitdepth = 10,                            -- 10-bit color depth display
  }
}

-- Register each monitor configuration for this host
for _, monitor in ipairs(monitors) do
  hl.monitor(monitor)
end

hl.config({
  -- Enable hardware cursors locally for this host (very smooth on Intel iGPU)
  cursor = {
    no_hardware_cursors = false,
  },
  -- Rendering optimizations for professional applications in fullscreen mode
  render = {
    direct_scanout = true,
  },
  decoration = {
    blur = {
      enabled = false,
    },
    shadow = {
      enabled = false,
    },
  },
})

-- 2. Host-Specific Window Routing Rules

-- 3. Host-Specific Workspace Rules
-- Workspace 1 opens on the primary Asus monitor and is set as default
hl.workspace_rule({ workspace = 1, monitor = "desc:ASUSTek COMPUTER INC XG32WCS TALMAS012758", default = true })

-- Workspace 2 opens on the top-left Dell monitor and is set as default
hl.workspace_rule({ workspace = 2, monitor = "desc:Dell Inc. DELL P2423DE 3PJ4CN3", default = true })

-- Workspace 8 opens on the bottom-left Sharp High-DPI monitor and is set as default
hl.workspace_rule({ workspace = 8, monitor = "desc:Sharp Corporation 0x1516", default = true })



