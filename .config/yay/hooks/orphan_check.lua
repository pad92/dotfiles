local known_maintainers = {}

local state_path = (os.getenv("XDG_DATA_HOME") or os.getenv("HOME") .. "/.local/share")
  .. "/yay/maintainers.lua"

local f = io.open(state_path, "r")
if f then
  local content = f:read("*a")
  f:close()
  local loader = (loadstring or load)(content)
  if loader then
    setfenv(loader, {})
    known_maintainers = loader() or {}
  end
end

yay.create_autocmd("UpgradeSelect", {
  desc = "flag orphaned or maintainer-changed AUR packages",
  callback = function(event)
    local updated = false

    for _, pkg in ipairs(event.data.upgrades) do
      if pkg.repository == "aur" then
        if pkg.maintainer == nil then
          yay.log.warn(pkg.name .. ": orphaned on AUR — review before upgrading")
        elseif known_maintainers[pkg.name] and known_maintainers[pkg.name] ~= pkg.maintainer then
          yay.log.warn(pkg.name .. ": maintainer changed from "
            .. known_maintainers[pkg.name] .. " to " .. pkg.maintainer)
        end

        if pkg.maintainer then
          known_maintainers[pkg.name] = pkg.maintainer
          updated = true
        end
      end
    end

    if updated then
      local dir = state_path:match("(.*/)")
      os.execute("mkdir -p '" .. dir:gsub("'", "'\\''") .. "'")
      local out = io.open(state_path, "w")
      if out then
        out:write("return {\n")
        for name, maintainer in pairs(known_maintainers) do
          out:write(string.format("  [%q] = %q,\n", name, maintainer))
        end
        out:write("}\n")
        out:close()
      end
    end
  end,
})
