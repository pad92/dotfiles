-- Places the connected monitors so that each one shares an edge with another,
-- using the size each monitor reports at run time. Nothing here knows a
-- resolution, a scale or a coordinate: Hyprland picks the mode and the scale,
-- this module turns relations such as "asus right of dell" into positions.
--
-- Software cannot see where the displays stand on the desk, so the relations
-- only say what the user wants. Every other case still gives a layout the
-- cursor can cross: a monitor with no spec, or whose neighbour is not
-- connected, goes to the right of the rightmost monitor.
--
-- A monitor spec (from hosts/settings.lua) is a table with:
--   name      unique layout name, used by the relations and the rules;
--   match     start of the EDID description, as Hyprland's "desc:" selector
--             matches it (for example "Dell Inc. DELL P2423DE"; add the
--             serial number to tell identical models apart), or
--   internal  true for the built-in panel of a laptop;
--   right_of, left_of, above, below
--             at most one, the layout name of the neighbour;
--   mode      optional mode policy for this monitor only (preferred, highrr
--             or highres), overriding the host-wide one;
--   bitdepth  optional 10 for a 10-bit framebuffer (HDR or wide-gamut
--             panels); Hyprland's 8 bits otherwise.
local M = {}

-- DRM connector types of a built-in panel. They name the kind of link, not a
-- particular machine.
local INTERNAL_CONNECTORS = { "eDP-", "LVDS-", "DSI-" }

local RELATIONS = { "right_of", "left_of", "above", "below" }

local function starts_with(text, prefix)
  return type(text) == "string" and text:sub(1, #prefix) == prefix
end

function M.is_internal(monitor)
  for _, prefix in ipairs(INTERNAL_CONNECTORS) do
    if starts_with(monitor.name, prefix) then
      return true
    end
  end
  return false
end

local function matches(spec, monitor)
  if spec.internal then
    return M.is_internal(monitor)
  end
  return type(spec.match) == "string" and spec.match ~= "" and starts_with(monitor.description, spec.match)
end

-- Size in layout coordinates: the mode divided by the scale, swapped when the
-- monitor is rotated by 90 or 270 degrees.
function M.logical_size(monitor)
  local scale = monitor.scale and monitor.scale > 0 and monitor.scale or 1
  local width = math.floor(monitor.width / scale + 0.5)
  local height = math.floor(monitor.height / scale + 0.5)
  if (monitor.transform or 0) % 2 == 1 then
    width, height = height, width
  end
  return width, height
end

local function relation_of(spec)
  for _, relation in ipairs(RELATIONS) do
    if spec[relation] then
      return relation, spec[relation]
    end
  end
  return nil, nil
end

-- Monitors sorted by connector name, so that identical models always pair
-- with their specs in the same order for the same cabling.
local function sorted_monitors(monitors)
  local sorted = {}
  for _, monitor in ipairs(monitors or {}) do
    table.insert(sorted, monitor)
  end
  table.sort(sorted, function(a, b)
    return a.name < b.name
  end)
  return sorted
end

-- Pairs each spec with one connected monitor. The most specific specs choose
-- first (the built-in panel, then the longest match), so a match that names
-- a serial number takes its monitor before a match on the model alone.
-- Returns { [spec name] = monitor }.
function M.assign(specs, monitors)
  local ranked = {}
  for index, spec in ipairs(specs or {}) do
    table.insert(ranked, { spec = spec, index = index })
  end
  local function weight(spec)
    return spec.internal and math.huge or #(spec.match or "")
  end
  table.sort(ranked, function(a, b)
    local wa, wb = weight(a.spec), weight(b.spec)
    if wa ~= wb then
      return wa > wb
    end
    return a.index < b.index
  end)

  local assigned, used = {}, {}
  local candidates = sorted_monitors(monitors)
  for _, entry in ipairs(ranked) do
    for _, monitor in ipairs(candidates) do
      if not used[monitor.name] and matches(entry.spec, monitor) then
        assigned[entry.spec.name] = monitor
        used[monitor.name] = true
        break
      end
    end
  end
  return assigned
end

local function place_next_to(relation, anchor, width, height)
  if relation == "right_of" then
    return anchor.x + anchor.width, anchor.y
  elseif relation == "left_of" then
    return anchor.x - width, anchor.y
  elseif relation == "below" then
    return anchor.x, anchor.y + anchor.height
  end
  return anchor.x, anchor.y - height
end

local function overlaps(a, b)
  return math.min(a.x + a.width, b.x + b.width) > math.max(a.x, b.x)
    and math.min(a.y + a.height, b.y + b.height) > math.max(a.y, b.y)
end

local function overlaps_any(box, placed)
  for _, other in pairs(placed) do
    if overlaps(box, other) then
      return true
    end
  end
  return false
end

-- Length of the edge two boxes share along the axis of `relation`: their
-- overlap across that axis, which must be positive for the cursor to cross.
local function shared_span(relation, a, b)
  if relation == "below" or relation == "above" then
    return math.min(a.x + a.width, b.x + b.width) - math.max(a.x, b.x)
  end
  return math.min(a.y + a.height, b.y + b.height) - math.max(a.y, b.y)
end

-- When the box next to its anchor overlaps another monitor, for example a
-- panel below a short monitor that would run under a taller neighbour, slides
-- it across the relation axis to the nearest place that still shares an edge
-- with the anchor and overlaps nothing. Returns false when there is none.
local function slide_along(relation, box, anchor, placed)
  local vertical = relation == "below" or relation == "above"
  local axis, size = vertical and "x" or "y", vertical and "width" or "height"
  local start = box[axis]
  local candidates = { anchor[axis], anchor[axis] + anchor[size] - box[size] }
  for _, other in pairs(placed) do
    table.insert(candidates, other[axis] - box[size])
    table.insert(candidates, other[axis] + other[size])
  end
  -- The nearest place wins, the smaller coordinate on a tie, so the result
  -- does not depend on the order in which `pairs` lists the monitors.
  local function nearer(value, best)
    local distance, best_distance = math.abs(value - start), math.abs(best - start)
    return distance < best_distance or (distance == best_distance and value < best)
  end
  local best
  for _, value in ipairs(candidates) do
    local trial = { x = box.x, y = box.y, width = box.width, height = box.height }
    trial[axis] = value
    if
      shared_span(relation, trial, anchor) > 0
      and not overlaps_any(trial, placed)
      and (not best or nearer(value, best))
    then
      best = value
    end
  end
  if best then
    box[axis] = best
    return true
  end
  return false
end

-- Moves a box further in the direction of its relation until it overlaps no
-- placed monitor. It then shares an edge with the monitor that blocked it, so
-- the cursor can still cross, though no longer with its anchor: the last
-- resort when sliding along finds no place.
local function clear_of(relation, box, placed)
  local moved = true
  while moved do
    moved = false
    for _, other in pairs(placed) do
      if overlaps(box, other) then
        if relation == "right_of" then
          box.x = other.x + other.width
        elseif relation == "left_of" then
          box.x = other.x - box.width
        elseif relation == "below" then
          box.y = other.y + other.height
        else
          box.y = other.y - box.height
        end
        moved = true
      end
    end
  end
  return box
end

-- The monitor whose right edge is furthest right, the top one on a tie.
local function rightmost(placed)
  local best
  for _, box in pairs(placed) do
    if
      not best
      or box.x + box.width > best.x + best.width
      or (box.x + box.width == best.x + best.width and box.y < best.y)
    then
      best = box
    end
  end
  return best
end

-- Returns { [connector] = "XxY" } for every connected monitor.
function M.compute(specs, monitors)
  local assigned = M.assign(specs, monitors)
  local sizes = {}
  for _, monitor in ipairs(monitors or {}) do
    local width, height = M.logical_size(monitor)
    sizes[monitor.name] = { width = width, height = height }
  end

  local placed = {}
  local function place(monitor, x, y, relation, anchor)
    local size = sizes[monitor.name]
    local box = { x = x, y = y, width = size.width, height = size.height }
    if relation and overlaps_any(box, placed) then
      if not (anchor and slide_along(relation, box, anchor, placed)) then
        clear_of(relation, box, placed)
      end
    end
    placed[monitor.name] = box
  end

  -- Specs whose monitor is connected, in the order the settings list them.
  local present = {}
  for _, spec in ipairs(specs or {}) do
    if assigned[spec.name] then
      table.insert(present, spec)
    end
  end

  -- The origin: the first connected spec without a relation, else the first
  -- connected spec, else the first monitor by connector name.
  local origin
  for _, spec in ipairs(present) do
    if not relation_of(spec) then
      origin = assigned[spec.name]
      break
    end
  end
  origin = origin or (present[1] and assigned[present[1].name]) or sorted_monitors(monitors)[1]
  if not origin then
    return {}
  end
  place(origin, 0, 0)

  -- Each pass places the specs whose neighbour is placed. A relation to a
  -- missing monitor or a cycle never resolves, so the loop ends.
  local progressed = true
  while progressed do
    progressed = false
    for _, spec in ipairs(present) do
      local monitor = assigned[spec.name]
      local relation, neighbour = relation_of(spec)
      local anchor = neighbour and assigned[neighbour] and placed[assigned[neighbour].name]
      if not placed[monitor.name] and anchor then
        local size = sizes[monitor.name]
        local x, y = place_next_to(relation, anchor, size.width, size.height)
        place(monitor, x, y, relation, anchor)
        progressed = true
      end
    end
  end

  -- Whatever is left (a neighbour that is not connected, a monitor no spec
  -- names) joins the right edge of the rightmost monitor.
  local leftover = {}
  for _, spec in ipairs(present) do
    table.insert(leftover, assigned[spec.name])
  end
  for _, monitor in ipairs(sorted_monitors(monitors)) do
    table.insert(leftover, monitor)
  end
  for _, monitor in ipairs(leftover) do
    if not placed[monitor.name] then
      local anchor = rightmost(placed)
      place(monitor, anchor.x + anchor.width, anchor.y, "right_of", anchor)
    end
  end

  -- Hyprland accepts negative positions, but some clients do not: shift the
  -- whole layout so that it starts at 0,0.
  local min_x, min_y = 0, 0
  for _, box in pairs(placed) do
    min_x = math.min(min_x, box.x)
    min_y = math.min(min_y, box.y)
  end

  local positions = {}
  for connector, box in pairs(placed) do
    positions[connector] = (box.x - min_x) .. "x" .. (box.y - min_y)
  end
  return positions
end

-- True when "desc:<match>" could select another monitor than the one the
-- layout gives this spec: another spec's match overlaps it, as two specs for
-- one model do, or several connected monitors start with it, as two
-- identical monitors do when only one spec names them. Hyprland would then
-- take the first in its own order, not in the layout's.
local function ambiguous(specs, spec, monitors)
  for _, other in ipairs(specs or {}) do
    if
      other ~= spec
      and other.match
      and (starts_with(other.match, spec.match) or starts_with(spec.match, other.match))
    then
      return true
    end
  end
  local count = 0
  for _, monitor in ipairs(monitors or {}) do
    if matches(spec, monitor) then
      count = count + 1
    end
  end
  return count > 1
end

-- The Hyprland selector of a layout name. A match that selects one monitor
-- only gives "desc:<match>", which also covers a monitor plugged in later.
-- The built-in panel and identical models give the connector they are
-- connected to, nil while they are not connected.
function M.selector(specs, name, monitors)
  for _, spec in ipairs(specs or {}) do
    if spec.name == name then
      if not spec.internal and not ambiguous(specs, spec, monitors) then
        return "desc:" .. spec.match
      end
      local monitor = M.assign(specs, monitors)[name]
      return monitor and monitor.name or nil
    end
  end
  return nil
end

-- The mode a policy picks among a monitor's available modes, as Hyprland
-- picks it: the EDID's preferred mode, the highest refresh rate then the
-- largest area (highrr), or the largest area then the highest refresh rate
-- (highres). nil when the monitor lists no mode.
function M.pick_mode(available, policy)
  local function area(m)
    return (m.width or 0) * (m.height or 0)
  end
  local function better(a, b)
    if policy == "highres" then
      if area(a) ~= area(b) then
        return area(a) > area(b)
      end
      return (a.refresh_rate or 0) > (b.refresh_rate or 0)
    end
    if (a.refresh_rate or 0) ~= (b.refresh_rate or 0) then
      return (a.refresh_rate or 0) > (b.refresh_rate or 0)
    end
    return area(a) > area(b)
  end
  local best
  for _, candidate in ipairs(available or {}) do
    if policy ~= "highrr" and policy ~= "highres" then
      if candidate.preferred then
        return candidate
      end
    elseif not best or better(candidate, best) then
      best = candidate
    end
  end
  return best
end

-- Returns the monitor rules for the connected monitors: the computed
-- position, with Hyprland's own choice of mode and scale. A spec's own mode
-- policy wins over the host-wide one: "highrr" on a 60 Hz office monitor
-- would pick a 75 Hz low resolution mode.
--
-- The positions are computed from the size of the mode each rule asks for,
-- when the monitor lists its modes, not from the size of the current mode:
-- a monitor that grows once its rule applies would otherwise overlap the
-- neighbour placed against its old edge until the next pass.
function M.rules(specs, monitors, mode)
  local by_name = {}
  for _, spec in ipairs(specs or {}) do
    by_name[spec.name] = spec
  end
  local mode_of, bitdepth_of = {}, {}
  for name, monitor in pairs(M.assign(specs, monitors)) do
    mode_of[monitor.name] = by_name[name].mode
    bitdepth_of[monitor.name] = by_name[name].bitdepth
  end
  for _, monitor in ipairs(monitors or {}) do
    mode_of[monitor.name] = mode_of[monitor.name] or mode or "preferred"
  end

  local targets = {}
  for _, monitor in ipairs(monitors or {}) do
    local target = {}
    for key, value in pairs(monitor) do
      target[key] = value
    end
    local picked = M.pick_mode(monitor.available_modes, mode_of[monitor.name])
    if picked and picked.width and picked.height then
      target.width, target.height = picked.width, picked.height
    end
    table.insert(targets, target)
  end
  local positions = M.compute(specs, targets)

  local rules = {}
  for _, monitor in ipairs(monitors or {}) do
    table.insert(rules, {
      output = monitor.name,
      mode = mode_of[monitor.name],
      position = positions[monitor.name],
      scale = "auto",
      bitdepth = bitdepth_of[monitor.name],
    })
  end
  return rules
end

return M
