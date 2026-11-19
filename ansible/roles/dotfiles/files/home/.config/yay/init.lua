local yay = rawget(_G, "yay")

-- yay v13 Lua configuration
-- Overlays config.json; CLI flags still take final precedence.

require("settings")

-- Each hook loads only when its YAY_<HOOK> switch is on (see hook_switch.lua).
local hook_switch = require("hook_switch")
for _, hook in ipairs({ "orphan_check", "recent_update", "pkgbuild_scan", "post_install" }) do
  if not hook_switch.disabled(hook) then
    require("hooks." .. hook)
  end
end

yay.log.debug("init.lua loaded")
