local yay = rawget(_G, "yay")

-- Each hook has an on/off switch in the environment, named after the hook;
-- init.lua checks it before loading the hook:
-- hooks.recent_update reads YAY_RECENT_UPDATE, hooks.post_install reads
-- YAY_POST_INSTALL, and so on. 0, off, false or no (any case, surrounding
-- spaces ignored) turn the hook off; any other value, or none, keeps it on.
-- Example for one run: YAY_RECENT_UPDATE=0 yay -Syu
local M = {}

local off_values = { ["0"] = true, off = true, ["false"] = true, no = true }

function M.disabled(hook)
  local var = "YAY_" .. hook:upper()
  local value = (os.getenv(var) or ""):match("^%s*(.-)%s*$"):lower()
  if off_values[value] then
    yay.log.warn(hook .. " hook disabled by " .. var .. "=" .. value)
    return true
  end
  return false
end

return M
