local M = {}

function M.load()
  local vars = {}
  local home = os.getenv("HOME")
  local file_path = home .. "/.config/hypr/hyprtoolkit.conf"
  local f = io.open(file_path, "r")
  if f then
    for line in f:lines() do
      local clean_line = line:gsub("#.*", "") -- Strip comments
      local key, val = clean_line:match("^%s*([%w_]+)%s*=%s*(.-)%s*$")
      if key and val then
        local hex = val:match("^0[xX](%x%x%x%x%x%x%x%x)$")
        if hex then
          local a = hex:sub(1, 2)
          local rgb = hex:sub(3, 8)
          if a:lower() == "ff" then
            vars[key] = "#" .. rgb
          else
            vars[key] = "#" .. rgb .. a
          end
        else
          local num = tonumber(val)
          if num then
            vars[key] = num
          else
            vars[key] = val
          end
        end
      end
    end
    f:close()
  end
  return vars
end

return M
