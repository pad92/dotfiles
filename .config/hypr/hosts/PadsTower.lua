-- =============================================================================
-- HOST-SPECIFIC CONFIGURATION: PadsTower (Desktop Gaming PC)
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

-- 2. Host-Specific Window Routing Rules
-- Forces Steam Big Picture Mode to Asus HDR Monitor
hl.window_rule({
  match = { class = "^(?i)(steam)$", title = "^(?i)(Steam Big Picture Mode)$" },
  monitor = "desc:ASUSTek COMPUTER INC XG32WCS TALMAS012758"
})

-- Forces Gamescope & Steam games to Asus HDR Monitor
hl.window_rule({
  match = { class = "^(?i)(gamescope|steam_app_.*)$" },
  monitor = "desc:ASUSTek COMPUTER INC XG32WCS TALMAS012758"
})

-- 3. Host-Specific Workspace Rules
hl.workspace_rule(
  -- Workspace 1 opens on the primary Asus monitor and is set as default
  { workspace = 1, monitor = "desc:ASUSTek COMPUTER INC XG32WCS TALMAS012758", default = true },
  
  -- Workspace 2 opens on the top-left Dell monitor and is set as default
  { workspace = 2, monitor = "desc:Dell Inc. DELL P2423DE 3PJ4CN3", default = true }
)
