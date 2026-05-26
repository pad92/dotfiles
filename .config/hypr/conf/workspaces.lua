-- =============================================================================
-- STATIC WORKSPACE TO MONITOR MAPPING CONFIGURATION
-- =============================================================================
-- Assigns specific workspaces to launch on specific physical monitors by default.

hl.workspace_rule(
  -- Workspace 1 opens on the primary Asus monitor and is set as default
  { workspace = 1, monitor = "desc:ASUSTek COMPUTER INC XG32WCS TALMAS012758", default = true },
  
  -- Workspace 2 opens on the top-left Dell monitor and is set as default
  { workspace = 2, monitor = "desc:Dell Inc. DELL P2423DE 3PJ4CN3", default = true },
  
  -- Workspace 8 opens on the bottom-left Sharp High-DPI monitor and is set as default
  { workspace = 8, monitor = "desc:Sharp Corporation 0x1516", default = true }
)
