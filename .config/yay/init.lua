-- yay v13 Lua configuration
-- Overlays config.json; CLI flags still take final precedence.

require("settings")
require("hooks.orphan_check")
require("hooks.recent_update")
require("hooks.pkgbuild_scan")
require("hooks.post_install")

yay.log.debug("init.lua loaded")
