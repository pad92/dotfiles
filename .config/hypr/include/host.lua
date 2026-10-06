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

  local function load_module(module, success_message, error_message)
    local status, err = pcall(require, module)
    if not status then
      table.insert(messages, error_message .. tostring(err))
      return false
    end

    table.insert(messages, success_message)
    return true
  end

  if hostname then
    local host_module = "hosts." .. hostname
    local found_path = package.searchpath(host_module, package.path)

    if found_path then
      return messages, load_module(host_module, "Host config loaded: " .. hostname, "Host config failed: ")
    else
      local default_module = "hosts.default"
      local default_found = package.searchpath(default_module, package.path)

      if default_found then
        return messages, load_module(default_module, "Default host config loaded", "Default host config failed: ")
      end
    end
  end

  table.insert(messages, "Host configuration could not be selected")
  return messages, false
end

return M
