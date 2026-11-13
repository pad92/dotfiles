-- Applies the host settings that Ansible renders into hosts/settings.lua from
-- the dotfiles_hypr_* variables. The deployment has already resolved the
-- machine's monitor relations and rules, so nothing here depends on the
-- hostname. include/layout.lua turns the relations into positions from the
-- monitors that are connected, again each time one is plugged or unplugged.
local hl = rawget(_G, "hl")
local layout = require("include.layout")

local M = {}

-- The monitors as plain tables, without the disabled and mirrored ones, which
-- take no place in the layout. `gone` is the name of a monitor that is being
-- removed and may still be listed.
local function connected_monitors(gone)
  local monitors = {}
  for _, monitor in ipairs(hl.get_monitors and hl.get_monitors() or {}) do
    if monitor.enabled ~= false and not monitor.is_mirror and monitor.name ~= gone then
      local modes = {}
      for _, mode in ipairs(monitor.available_modes or {}) do
        table.insert(modes, {
          width = mode.width,
          height = mode.height,
          refresh_rate = mode.refresh_rate,
          preferred = mode.preferred,
        })
      end
      table.insert(monitors, {
        name = monitor.name,
        description = monitor.description,
        width = monitor.width,
        height = monitor.height,
        scale = monitor.scale,
        transform = monitor.transform,
        available_modes = modes,
      })
    end
  end
  return monitors
end

-- Sends the monitor rules that differ from the last ones sent. The layout
-- uses the size of the mode each rule asks for, but the scale is read before
-- Hyprland applies the "auto" one, so the layout is computed again once it
-- has (monitor.layout_changed); the comparison stops that loop as soon as
-- the positions are stable.
local function arrange(settings, monitors, sent)
  local connected = {}
  for _, rule in ipairs(layout.rules(settings.monitors, monitors, settings.monitor_mode)) do
    connected[rule.output] = true
    local key = table.concat({ rule.mode, rule.position, rule.scale, tostring(rule.bitdepth) }, " ")
    if sent[rule.output] ~= key then
      hl.monitor(rule)
      sent[rule.output] = key
    end
  end
  for output in pairs(sent) do
    if not connected[output] then
      sent[output] = nil
    end
  end
end

-- Workspace and window rules name a layout monitor. Its selector can change:
-- the built-in panel and identical models resolve to a connector, unknown
-- until the monitor is listed (on the first start Hyprland reads the
-- configuration before it lists the monitors) and possibly different after
-- a hotplug. A rule is therefore created again, and the old one disabled,
-- whenever its selector changes.
local function named_rules(settings)
  local items = {}
  for _, rule in ipairs(settings.workspace_rules or {}) do
    table.insert(items, { apply = hl.workspace_rule, rule = rule })
  end
  for _, rule in ipairs(settings.window_rules or {}) do
    table.insert(items, { apply = hl.window_rule, rule = rule })
  end
  if settings.touch_monitor then
    table.insert(items, {
      apply = function(rule)
        hl.config({ input = { touchdevice = { output = rule.monitor } } })
      end,
      rule = { monitor = settings.touch_monitor },
    })
  end
  return items
end

local function apply_rules(settings, items, monitors)
  for _, item in ipairs(items) do
    local selector = layout.selector(settings.monitors, item.rule.monitor, monitors)
    if selector ~= item.selector and item.handle and item.handle.set_enabled then
      -- A rule on a connector must not follow another monitor plugged in
      -- there later, so it goes as soon as its monitor does.
      item.handle:set_enabled(false)
      item.handle = nil
    end
    if not selector then
      item.selector = nil
    elseif selector ~= item.selector then
      local rule = {}
      for key, value in pairs(item.rule) do
        rule[key] = value
      end
      rule.monitor = selector
      item.handle = item.apply(rule)
      item.selector = selector
    end
  end
end

-- The connector of the monitor an event passes. Hyprland raises an error when
-- a field of a monitor it has destroyed is read, which a removal may pass.
local function name_of(monitor)
  if type(monitor) == "string" then
    return monitor
  end
  local ok, name = pcall(function()
    return monitor and monitor.name
  end)
  return ok and name or nil
end

-- An event handler that reports its error instead of failing silently: an
-- error there would leave the monitors where they were, possibly apart.
local function guarded(handler)
  return function(...)
    local ok, err = pcall(handler, ...)
    if not ok and hl.notification and hl.notification.create then
      pcall(hl.notification.create, { text = "Monitor layout failed: " .. tostring(err) })
    end
  end
end

local function apply(settings)
  if next(settings.config or {}) then
    hl.config(settings.config)
  end

  local items, sent = named_rules(settings), {}
  local function refresh(gone)
    local monitors = connected_monitors(gone)
    arrange(settings, monitors, sent)
    apply_rules(settings, items, monitors)
  end

  refresh()
  if hl.on then
    hl.on("hyprland.start", guarded(refresh))
    hl.on("monitor.added", guarded(refresh))
    hl.on("monitor.layout_changed", guarded(refresh))
    hl.on(
      "monitor.removed",
      guarded(function(monitor)
        refresh(name_of(monitor))
      end)
    )
  end
end

function M.load()
  local messages = {}

  local loaded, settings = pcall(require, "hosts.settings")
  if not loaded then
    table.insert(messages, "Host settings failed: " .. tostring(settings))
    return messages, false
  end

  local applied, err = pcall(apply, settings)
  if not applied then
    table.insert(messages, "Host settings failed: " .. tostring(err))
    return messages, false
  end

  table.insert(messages, "Host settings loaded")
  return messages, true
end

return M
