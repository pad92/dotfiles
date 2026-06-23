local M = {}

local function get_hostname()
  local hostname = os.getenv("HOSTNAME") or os.getenv("HOST")
  if not hostname then
    local file = io.open("/proc/sys/kernel/hostname", "r")
    if file then
      hostname = file:read("*a")
      file:close()
    end
  end

  if hostname then
    hostname = hostname:gsub("%s+", "")
  else
    local handle = io.popen("hostname")
    if handle then
      hostname = handle:read("*a"):gsub("%s+", "")
      handle:close()
    end
  end
  return hostname
end

function M.load()
  local hostname = get_hostname()
  local messages = {}

  if hostname then
    local host_module = "hosts." .. hostname
    local found_path = package.searchpath(host_module, package.path)

    if found_path then
      local status, err = pcall(require, host_module)
      if status then
        table.insert(messages, "Host config loaded: " .. hostname)
      else
        print("Error loading host configuration: " .. tostring(err))
      end
    else
      local default_module = "hosts.default"
      local default_found = package.searchpath(default_module, package.path)

      if default_found then
        local status, err = pcall(require, default_module)
        if status then
          table.insert(messages, "Default host config loaded")
        else
          print("Error loading default host configuration: " .. tostring(err))
        end
      end
    end
  end

  return messages
end

return M
