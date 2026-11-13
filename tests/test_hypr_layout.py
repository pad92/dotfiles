"""Run the Hyprland monitor layout (include/layout.lua and include/host.lua).

The layout must let the cursor cross between every pair of neighbours, so the
main property checked here is that each placed monitor shares an edge segment
with another one, computed from the sizes the monitors report, not from
positions written in the configuration.
"""

import itertools
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HYPR = ROOT / "ansible/roles/dotfiles/files/home/.config/hypr"
LUA = shutil.which("lua") or shutil.which("luajit") or ""

# Monitors as PadsP5560 reports them: the Sharp panel is 3840x2400 at scale 2,
# so 1920x1200 in layout coordinates; the externals are 2560x1440 at scale 1.
LAPTOP = {
    "name": "eDP-1",
    "description": "Sharp Corporation 0x1516",
    "width": 3840,
    "height": 2400,
    "scale": 2,
    "transform": 0,
}
DELL = {
    "name": "DP-2",
    "description": "Dell Inc. DELL P2423DE 0000001",
    "width": 2560,
    "height": 1440,
    "scale": 1,
    "transform": 0,
}
ASUS = {
    "name": "DP-3",
    "description": "ASUSTek COMPUTER INC XG32WCS 0000002",
    "width": 2560,
    "height": 1440,
    "scale": 1,
    "transform": 0,
}
DELL_TWIN = dict(DELL, name="DP-4", description="Dell Inc. DELL P2423DE 9ZZZZZZ")
STRANGER = {
    "name": "HDMI-A-1",
    "description": "Acme Corp X1 0001",
    "width": 1920,
    "height": 1080,
    "scale": 1,
    "transform": 0,
}
TWIN_SPECS = [
    {"name": "left", "match": "Dell Inc. DELL P2423DE"},
    {"name": "right", "match": "Dell Inc. DELL P2423DE", "right_of": "left"},
]
SPECS = [
    {"name": "dell", "match": "Dell Inc. DELL P2423DE"},
    {"name": "asus", "match": "ASUSTek COMPUTER INC XG32WCS", "right_of": "dell"},
    {"name": "laptop", "internal": True, "below": "dell"},
]

# The specs and monitors go in as a Lua literal; the result comes back as
# "connector<TAB>position" lines.
LAYOUT_SCRIPT = """
package.path = arg[1] .. "/?.lua;" .. package.path
local layout = require("include.layout")
local input = load("return " .. io.read("*a"))()
local positions = layout.compute(input.specs, input.monitors)
for connector, position in pairs(positions) do
  print(connector .. "\\t" .. position)
end
"""


def lua_literal(value):
    """Render Python data as a Lua literal for the test input."""
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, dict):
        return (
            "{"
            + ", ".join(
                f"[{json.dumps(k)}] = {lua_literal(v)}" for k, v in value.items()
            )
            + "}"
        )
    return "{" + ", ".join(lua_literal(item) for item in value) + "}"


def logical_box(monitor, position):
    x, y = (int(part) for part in position.split("x"))
    width = round(monitor["width"] / monitor["scale"])
    height = round(monitor["height"] / monitor["scale"])
    if monitor.get("transform", 0) % 2 == 1:
        width, height = height, width
    return x, y, width, height


def share_edge(first, second):
    """True when two boxes touch along a segment longer than a point."""
    ax, ay, aw, ah = first
    bx, by, bw, bh = second
    vertical_overlap = min(ay + ah, by + bh) - max(ay, by)
    horizontal_overlap = min(ax + aw, bx + bw) - max(ax, bx)
    side_by_side = (ax + aw == bx or bx + bw == ax) and vertical_overlap > 0
    stacked = (ay + ah == by or by + bh == ay) and horizontal_overlap > 0
    return side_by_side or stacked


def overlap(first, second):
    ax, ay, aw, ah = first
    bx, by, bw, bh = second
    return min(ax + aw, bx + bw) > max(ax, bx) and min(ay + ah, by + bh) > max(ay, by)


@unittest.skipUnless(LUA, "requires lua or luajit")
class LayoutTests(unittest.TestCase):
    def compute(self, specs, monitors):
        result = subprocess.run(
            [LUA, "-", str(HYPR)],
            input=LAYOUT_SCRIPT.replace(
                'io.read("*a")',
                json.dumps(lua_literal({"specs": specs, "monitors": monitors})),
            ),
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        return dict(line.split("\t") for line in result.stdout.splitlines())

    def assert_connected_without_overlap(self, monitors, positions):
        """Every monitor is reachable from every other across shared edges."""
        self.assertEqual(sorted(positions), sorted(m["name"] for m in monitors))
        boxes = {m["name"]: logical_box(m, positions[m["name"]]) for m in monitors}
        names = sorted(boxes)
        for index, name in enumerate(names):
            for other in names[index + 1 :]:
                self.assertFalse(overlap(boxes[name], boxes[other]), boxes)
        reached, frontier = {names[0]}, [names[0]]
        while frontier:
            current = frontier.pop()
            for other in names:
                if other not in reached and share_edge(boxes[current], boxes[other]):
                    reached.add(other)
                    frontier.append(other)
        self.assertEqual(reached, set(names), f"not connected: {boxes}")

    def assert_relations_hold(self, specs, monitors, positions):
        """Each described monitor shares an edge with the neighbour it names,
        on the side its relation says."""
        by_spec = {}
        for spec in specs:
            for monitor in monitors:
                if monitor["name"] in by_spec.values():
                    continue
                if (spec.get("internal") and monitor["name"].startswith("eDP-")) or (
                    "match" in spec and monitor["description"].startswith(spec["match"])
                ):
                    by_spec[spec["name"]] = monitor["name"]
                    break
        boxes = {m["name"]: logical_box(m, positions[m["name"]]) for m in monitors}
        for spec in specs:
            for relation in ("right_of", "left_of", "above", "below"):
                if (
                    relation in spec
                    and spec["name"] in by_spec
                    and spec[relation] in by_spec
                ):
                    x, y, w, h = boxes[by_spec[spec["name"]]]
                    ax, ay, aw, ah = boxes[by_spec[spec[relation]]]
                    side = {
                        "right_of": x == ax + aw,
                        "left_of": x + w == ax,
                        "below": y == ay + ah,
                        "above": y + h == ay,
                    }[relation]
                    self.assertTrue(
                        side
                        and share_edge(
                            boxes[by_spec[spec["name"]]], boxes[by_spec[spec[relation]]]
                        ),
                        f"{spec['name']} not {relation} {spec[relation]}: {boxes}",
                    )

    def test_laptop_sits_under_the_dell_and_the_asus_right_of_it(self):
        monitors = [LAPTOP, DELL, ASUS]
        positions = self.compute(SPECS, monitors)
        self.assertEqual(
            positions, {"DP-2": "0x0", "DP-3": "2560x0", "eDP-1": "0x1440"}
        )
        self.assert_connected_without_overlap(monitors, positions)

    # The layout Hyprland ran before this change: the panel fixed at 0x1440,
    # the externals auto-placed to its right. It touches only at a corner,
    # which is the reported bug; the property check must reject it.
    def test_the_edge_check_rejects_the_corner_only_layout_of_the_bug(self):
        with self.assertRaises(AssertionError):
            self.assert_connected_without_overlap(
                [LAPTOP, DELL, ASUS],
                {"eDP-1": "0x1440", "DP-2": "1920x0", "DP-3": "4480x0"},
            )

    def test_positions_follow_the_reported_size_not_a_fixed_resolution(self):
        dell = dict(DELL, width=1920, height=1080)
        # 1920x1200 at scale 1.25 is 1536x960 in layout coordinates.
        laptop = dict(LAPTOP, width=1920, height=1200, scale=1.25)
        monitors = [laptop, dell, ASUS]
        positions = self.compute(SPECS, monitors)
        self.assertEqual(
            positions, {"DP-2": "0x0", "DP-3": "1920x0", "eDP-1": "0x1080"}
        )
        self.assert_connected_without_overlap(monitors, positions)

    # A panel wider than the Dell would run under the taller ASUS. Pushed
    # down to the ASUS's bottom edge, it would leave a gap under the Dell, so
    # it slides left instead: right-aligned with the Dell, still below it.
    def test_a_wide_panel_below_a_short_monitor_slides_and_keeps_its_edge(self):
        dell = dict(DELL, width=1920, height=1080)
        # 2560x1600 at scale 1.25 is 2048x1280 in layout coordinates.
        laptop = dict(LAPTOP, width=2560, height=1600, scale=1.25)
        monitors = [laptop, dell, ASUS]
        positions = self.compute(SPECS, monitors)
        self.assertEqual(
            positions, {"DP-2": "128x0", "DP-3": "2048x0", "eDP-1": "0x1080"}
        )
        self.assert_connected_without_overlap(monitors, positions)
        self.assert_relations_hold(SPECS, monitors, positions)

    # Same with a portrait ASUS, 2560 tall: the old push left 1120 px free
    # under the Dell.
    def test_a_wide_panel_slides_past_a_portrait_neighbour(self):
        laptop = dict(LAPTOP, width=3200, height=2000, scale=1)
        monitors = [laptop, DELL, dict(ASUS, transform=1)]
        positions = self.compute(SPECS, monitors)
        self.assertEqual(
            positions, {"DP-2": "640x0", "DP-3": "3200x0", "eDP-1": "0x1440"}
        )
        self.assert_relations_hold(SPECS, monitors, positions)

    def test_a_rotated_monitor_uses_its_rotated_size(self):
        specs = [
            {"name": "dell", "match": "Dell Inc. DELL P2423DE"},
            {
                "name": "asus",
                "match": "ASUSTek COMPUTER INC XG32WCS",
                "left_of": "dell",
            },
        ]
        asus = dict(ASUS, transform=1)
        positions = self.compute(specs, [DELL, asus])
        # The portrait ASUS is 1440 wide: the layout shifts to start at 0,0.
        self.assertEqual(positions, {"DP-3": "0x0", "DP-2": "1440x0"})
        self.assert_connected_without_overlap([DELL, asus], positions)

    def test_above_shifts_the_layout_to_non_negative_coordinates(self):
        specs = [
            {"name": "laptop", "internal": True},
            {"name": "dell", "match": "Dell Inc. DELL P2423DE", "above": "laptop"},
        ]
        positions = self.compute(specs, [LAPTOP, DELL])
        self.assertEqual(positions, {"DP-2": "0x0", "eDP-1": "0x1440"})

    # Without the Dell, the ASUS becomes the origin; the panel's neighbour is
    # gone, so it joins the right edge of the layout instead of floating.
    def test_missing_anchor_joins_the_rightmost_monitor(self):
        monitors = [LAPTOP, ASUS]
        positions = self.compute(SPECS, monitors)
        self.assertEqual(positions, {"DP-3": "0x0", "eDP-1": "2560x0"})
        self.assert_connected_without_overlap(monitors, positions)

    def test_laptop_alone_is_at_the_origin(self):
        self.assertEqual(self.compute(SPECS, [LAPTOP]), {"eDP-1": "0x0"})

    def test_unknown_monitor_joins_the_rightmost_monitor(self):
        monitors = [LAPTOP, DELL, ASUS, STRANGER]
        positions = self.compute(SPECS, monitors)
        self.assertEqual(positions["HDMI-A-1"], "5120x0")
        self.assert_connected_without_overlap(monitors, positions)

    def test_without_any_spec_every_monitor_is_still_reachable(self):
        monitors = [ASUS, LAPTOP, STRANGER, DELL]
        positions = self.compute([], monitors)
        # Connector order: DP-2, DP-3, HDMI-A-1, eDP-1 (uppercase sorts first).
        self.assertEqual(
            positions,
            {"DP-2": "0x0", "DP-3": "2560x0", "HDMI-A-1": "5120x0", "eDP-1": "7040x0"},
        )
        self.assert_connected_without_overlap(monitors, positions)

    # Every subset of monitors, under every kind of settings, must give one
    # connected layout without overlap: "it works in every case".
    def test_every_combination_is_connected_without_overlap(self):
        rotated_asus = dict(ASUS, transform=3)
        pool = [LAPTOP, DELL, DELL_TWIN, rotated_asus, STRANGER]
        spec_sets = {
            "workstation": SPECS,
            "none": [],
            "twins": TWIN_SPECS
            + [{"name": "laptop", "internal": True, "above": "left"}],
            "cycle": [
                {"name": "a", "match": "Dell Inc. DELL P2423DE", "below": "b"},
                {"name": "b", "internal": True, "left_of": "a"},
            ],
            "absent anchor": [
                {
                    "name": "asus",
                    "match": "ASUSTek COMPUTER INC XG32WCS",
                    "left_of": "lg",
                },
                {"name": "lg", "match": "LG Electronics"},
            ],
        }
        for label, specs in spec_sets.items():
            for size in range(1, len(pool) + 1):
                for monitors in itertools.combinations(pool, size):
                    names = "+".join(m["name"] for m in monitors)
                    with self.subTest(settings=label, monitors=names):
                        positions = self.compute(specs, list(monitors))
                        self.assert_connected_without_overlap(list(monitors), positions)
                        # Acyclic relations between monitors that are both
                        # connected must also hold, not just connectivity.
                        if label in ("workstation", "twins"):
                            self.assert_relations_hold(specs, list(monitors), positions)

    # Two Dells of one model differ only by serial number. Without it, the
    # connector name decides, so the same cabling always gives the same layout.
    def test_identical_models_pair_by_connector_name(self):
        positions = self.compute(TWIN_SPECS, [DELL_TWIN, DELL])
        self.assertEqual(positions, {"DP-2": "0x0", "DP-4": "2560x0"})

    def test_a_match_with_the_serial_number_takes_its_own_monitor(self):
        specs = [
            {"name": "left", "match": "Dell Inc. DELL P2423DE"},
            {
                "name": "right",
                "match": "Dell Inc. DELL P2423DE 0000001",
                "right_of": "left",
            },
        ]
        # 0000001 is on DP-2: it goes right although DP-2 sorts first.
        positions = self.compute(specs, [DELL, DELL_TWIN])
        self.assertEqual(positions, {"DP-4": "0x0", "DP-2": "2560x0"})

    def test_cyclic_relations_terminate(self):
        specs = [
            {"name": "dell", "match": "Dell Inc. DELL P2423DE", "right_of": "asus"},
            {
                "name": "asus",
                "match": "ASUSTek COMPUTER INC XG32WCS",
                "right_of": "dell",
            },
        ]
        positions = self.compute(specs, [DELL, ASUS])
        self.assertEqual(positions, {"DP-2": "0x0", "DP-3": "2560x0"})

    # "DELL P2423DE" is not the start of the description: like Hyprland's
    # desc: selector, it does not match, so the Dell is not put left.
    def test_description_must_start_with_the_match_like_hyprland_desc(self):
        specs = [
            {"name": "laptop", "internal": True},
            {"name": "dell", "match": "DELL P2423DE", "left_of": "laptop"},
        ]
        positions = self.compute(specs, [LAPTOP, DELL])
        self.assertEqual(positions, {"eDP-1": "0x0", "DP-2": "1920x0"})


# layout.rules() as "connector<TAB>mode<TAB>position" lines.
RULES_SCRIPT = """
package.path = arg[1] .. "/?.lua;" .. package.path
local layout = require("include.layout")
local input = load("return " .. io.read("*a"))()
for _, rule in ipairs(layout.rules(input.specs, input.monitors, input.mode)) do
  print(rule.output .. "\\t" .. rule.mode .. "\\t" .. rule.position)
end
"""


def mode(width, height, refresh_rate, preferred=False):
    return {
        "width": width,
        "height": height,
        "refresh_rate": refresh_rate,
        "preferred": preferred,
    }


# The modes PadsTower's monitors list, shortened: the Dell offers 75 Hz only
# at low resolutions, the ASUS 180 Hz at its native one.
DELL_MODES = [
    mode(2560, 1440, 59.951, preferred=True),
    mode(1280, 1024, 75.025),
    mode(1024, 768, 75.029),
    mode(640, 480, 60.0),
]
ASUS_MODES = [
    mode(2560, 1440, 59.951, preferred=True),
    mode(2560, 1440, 180.0),
    mode(1920, 1080, 120.0),
]


@unittest.skipUnless(LUA, "requires lua or luajit")
class RulesTests(unittest.TestCase):
    def rules(self, specs, monitors, policy):
        result = subprocess.run(
            [LUA, "-", str(HYPR)],
            input=RULES_SCRIPT.replace(
                'io.read("*a")',
                json.dumps(
                    lua_literal({"specs": specs, "monitors": monitors, "mode": policy})
                ),
            ),
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        return {
            output: (rule_mode, position)
            for output, rule_mode, position in (
                line.split("\t") for line in result.stdout.splitlines()
            )
        }

    def test_a_monitor_mode_overrides_the_host_policy(self):
        specs = [
            {"name": "dell", "match": "Dell Inc. DELL P2423DE", "mode": "preferred"},
            {
                "name": "asus",
                "match": "ASUSTek COMPUTER INC XG32WCS",
                "right_of": "dell",
            },
        ]
        monitors = [
            dict(DELL, available_modes=DELL_MODES),
            dict(ASUS, available_modes=ASUS_MODES),
        ]
        self.assertEqual(
            self.rules(specs, monitors, "highrr"),
            {"DP-2": ("preferred", "0x0"), "DP-3": ("highrr", "2560x0")},
        )

    def test_positions_use_the_size_of_the_requested_mode(self):
        # The Dell still runs the 1024x768 mode an earlier highrr policy gave
        # it. Placed from that size, the ASUS would land at 1024x0 and overlap
        # the Dell once it is back at 2560x1440.
        specs = [
            {"name": "dell", "match": "Dell Inc. DELL P2423DE", "mode": "preferred"},
            {
                "name": "asus",
                "match": "ASUSTek COMPUTER INC XG32WCS",
                "right_of": "dell",
            },
        ]
        monitors = [
            dict(DELL, width=1024, height=768, available_modes=DELL_MODES),
            dict(ASUS, available_modes=ASUS_MODES),
        ]
        self.assertEqual(
            self.rules(specs, monitors, "highrr"),
            {"DP-2": ("preferred", "0x0"), "DP-3": ("highrr", "2560x0")},
        )

    def test_the_host_policy_picks_the_size_it_will_get(self):
        # Without its own mode, the Dell gets highrr and its 75 Hz 1024x768
        # mode, so the ASUS stands against that narrower edge.
        monitors = [
            dict(DELL, available_modes=DELL_MODES),
            dict(ASUS, available_modes=ASUS_MODES),
        ]
        self.assertEqual(
            self.rules(SPECS[:2], monitors, "highrr"),
            {"DP-2": ("highrr", "0x0"), "DP-3": ("highrr", "1024x0")},
        )
        self.assertEqual(
            self.rules(SPECS[:2], monitors, "highres"),
            {"DP-2": ("highres", "0x0"), "DP-3": ("highres", "2560x0")},
        )

    def test_without_listed_modes_the_current_size_is_used(self):
        monitors = [dict(DELL, width=1024, height=768), ASUS]
        self.assertEqual(
            self.rules(SPECS[:2], monitors, None),
            {"DP-2": ("preferred", "0x0"), "DP-3": ("preferred", "1024x0")},
        )


# include/host.lua against a recording stand-in for the hl API, with
# monitors that change between events as a hotplug would.
HOST_SCRIPT = """
package.path = arg[1] .. "/?.lua;" .. package.path
local state = load("return " .. io.read("*a"))()
local calls, handlers = {}, {}
local monitors = state.initial
-- Rules return a handle, as Hyprland's do; disabling it is recorded.
local function record(kind)
  return function(value)
    table.insert(calls, { kind = kind, value = value })
    return {
      set_enabled = function(_, enabled)
        table.insert(calls, { kind = "enabled=" .. tostring(enabled), value = value })
      end,
    }
  end
end
_G.hl = {
  monitor = record("monitor"),
  workspace_rule = record("workspace_rule"),
  window_rule = record("window_rule"),
  config = record("config"),
  get_monitors = function()
    if monitors == "fail" then error("get_monitors failed") end
    return monitors
  end,
  on = function(event, handler) handlers[event] = handler end,
  notification = { create = function(value) table.insert(calls, { kind = "notification", value = value }) end },
}
-- A monitor Hyprland has destroyed: reading any field raises an error.
local expired = setmetatable({}, { __index = function() error("HL.Monitor(expired)") end })
package.loaded["hosts.settings"] = state.settings
local messages, loaded = require("include.host").load()
print("loaded", tostring(loaded), table.concat(messages, "|"))
calls = {}
for _, step in ipairs(state.steps) do
  monitors = step.monitors
  print("event", step.event)
  handlers[step.event](step.argument == "expired" and expired or step.argument)
  for _, call in ipairs(calls) do
    local v = call.value
    local touch = v.input and v.input.touchdevice and v.input.touchdevice.output
    print(call.kind, v.output or v.monitor or touch or v.text or "", v.position or tostring(v.workspace or ""),
      v.mode or "", tostring(v.scale or ""))
  end
  calls = {}
end
"""


HOST_SETTINGS = {
    "monitor_mode": "preferred",
    "monitors": SPECS,
    "workspace_rules": [
        {"workspace": 2, "monitor": "dell", "default": True},
        {"workspace": 8, "monitor": "laptop", "default": True},
    ],
    "window_rules": [],
    "touch_monitor": "laptop",
    "config": {},
}


@unittest.skipUnless(LUA, "requires lua or luajit")
class HostTests(unittest.TestCase):
    def run_host(self, initial, steps, settings=None):
        with tempfile.TemporaryDirectory() as work:
            config = Path(work) / "hypr"
            shutil.copytree(HYPR / "include", config / "include")
            state = {
                "settings": settings or HOST_SETTINGS,
                "initial": initial,
                "steps": steps,
            }
            script = HOST_SCRIPT.replace(
                'io.read("*a")', json.dumps(lua_literal(state))
            )
            result = subprocess.run(
                [LUA, "-", str(config)],
                input=script,
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
        lines = [line.split("\t") for line in result.stdout.splitlines()]
        self.assertEqual(lines[0], ["loaded", "true", "Host settings loaded"])
        events, current = {}, None
        for line in lines[1:]:
            if line[0] == "event":
                current = line[1]
                events[current] = []
            else:
                events[current].append(tuple(line))
        return events

    # On the first start Hyprland reads the configuration before it lists the
    # monitors: the start event places them and the panel's rules then apply.
    def test_start_places_monitors_and_applies_panel_rules(self):
        events = self.run_host(
            [], [{"event": "hyprland.start", "monitors": [LAPTOP, DELL, ASUS]}]
        )
        calls = events["hyprland.start"]
        self.assertIn(("monitor", "eDP-1", "0x1440", "preferred", "auto"), calls)
        self.assertIn(("monitor", "DP-2", "0x0", "preferred", "auto"), calls)
        self.assertIn(("monitor", "DP-3", "2560x0", "preferred", "auto"), calls)
        self.assertIn(("workspace_rule", "eDP-1", "8", "", ""), calls)
        self.assertIn(("config", "eDP-1", "", "", ""), calls)

    def test_hotplug_recomputes_and_skips_the_removed_monitor(self):
        events = self.run_host(
            [LAPTOP],
            [
                {"event": "monitor.added", "monitors": [LAPTOP, DELL]},
                # Hyprland may still list the monitor it is removing.
                {
                    "event": "monitor.removed",
                    "monitors": [LAPTOP, DELL],
                    "argument": DELL,
                },
            ],
        )
        added = [call for call in events["monitor.added"] if call[0] == "monitor"]
        self.assertEqual(
            sorted(added),
            [
                ("monitor", "DP-2", "0x0", "preferred", "auto"),
                ("monitor", "eDP-1", "0x1440", "preferred", "auto"),
            ],
        )
        removed = [call for call in events["monitor.removed"] if call[0] == "monitor"]
        self.assertEqual(removed, [("monitor", "eDP-1", "0x0", "preferred", "auto")])
        # The panel's rules were applied at load; they are not applied twice.
        self.assertNotIn(
            "workspace_rule", [call[0] for call in events["monitor.added"]]
        )

    # Two identical Dells: "desc:" would select both, so the rule follows the
    # connector of the one named "right", and moves when the cabling changes.
    def test_rule_on_an_identical_model_follows_its_connector(self):
        settings = {
            "monitors": TWIN_SPECS,
            "workspace_rules": [{"workspace": 3, "monitor": "right"}],
        }
        swapped = dict(DELL_TWIN, name="DP-1")
        events = self.run_host(
            [],
            [
                {"event": "hyprland.start", "monitors": [DELL, DELL_TWIN]},
                # The twin moves to DP-1, which now sorts first: "left".
                {"event": "monitor.added", "monitors": [DELL, swapped]},
            ],
            settings,
        )
        start = [c for c in events["hyprland.start"] if c[0] != "monitor"]
        self.assertEqual(start, [("workspace_rule", "DP-4", "3", "", "")])
        added = [c for c in events["monitor.added"] if c[0] != "monitor"]
        self.assertEqual(
            added,
            [
                ("enabled=false", "DP-4", "3", "", ""),
                ("workspace_rule", "DP-2", "3", "", ""),
            ],
        )

    # Sending a rule makes Hyprland report a layout change. When the positions
    # computed again are the same, nothing is sent, so the rules do not loop.
    def test_an_unchanged_layout_sends_no_rule_again(self):
        unscaled = dict(LAPTOP, scale=1)
        events = self.run_host(
            [],
            [
                {"event": "hyprland.start", "monitors": [unscaled, DELL]},
                {"event": "monitor.layout_changed", "monitors": [LAPTOP, DELL]},
                {"event": "monitor.layout_changed", "monitors": [LAPTOP, DELL]},
            ],
        )
        # The panel below the Dell stays at 0x1440 whatever its scale.
        self.assertIn(
            ("monitor", "eDP-1", "0x1440", "preferred", "auto"),
            events["hyprland.start"],
        )
        self.assertEqual(events["monitor.layout_changed"], [])

    # The sizes read when a rule is sent are those of the old mode and scale
    # (here the panel still at scale 1). Once Hyprland has applied the rule,
    # the layout is computed again with the real size.
    def test_a_size_change_moves_the_monitors_that_depend_on_it(self):
        settings = dict(
            HOST_SETTINGS,
            monitors=[
                {"name": "laptop", "internal": True},
                {
                    "name": "dell",
                    "match": "Dell Inc. DELL P2423DE",
                    "right_of": "laptop",
                },
            ],
        )
        events = self.run_host(
            [],
            [
                {"event": "hyprland.start", "monitors": [dict(LAPTOP, scale=1), DELL]},
                {"event": "monitor.layout_changed", "monitors": [LAPTOP, DELL]},
            ],
            settings,
        )
        self.assertIn(
            ("monitor", "DP-2", "3840x0", "preferred", "auto"), events["hyprland.start"]
        )
        changed = [c for c in events["monitor.layout_changed"] if c[0] == "monitor"]
        self.assertEqual(changed, [("monitor", "DP-2", "1920x0", "preferred", "auto")])

    # Reading the removed monitor may raise; the layout must still follow.
    def test_removal_of_an_expired_monitor_still_rearranges(self):
        events = self.run_host(
            [LAPTOP, DELL, ASUS],
            [
                {
                    "event": "monitor.removed",
                    "monitors": [LAPTOP, ASUS],
                    "argument": "expired",
                }
            ],
        )
        moved = sorted(c for c in events["monitor.removed"] if c[0] == "monitor")
        self.assertEqual(
            moved,
            [
                ("monitor", "DP-3", "0x0", "preferred", "auto"),
                ("monitor", "eDP-1", "2560x0", "preferred", "auto"),
            ],
        )

    def test_a_failing_handler_reports_instead_of_raising(self):
        events = self.run_host(
            [LAPTOP], [{"event": "monitor.added", "monitors": "fail"}]
        )
        self.assertEqual(len(events["monitor.added"]), 1)
        self.assertEqual(events["monitor.added"][0][0], "notification")
        self.assertIn("get_monitors failed", events["monitor.added"][0][1])

    # A rule on a connector goes with its monitor, so that another monitor
    # plugged into that connector later does not inherit it.
    def test_rule_on_a_connector_is_disabled_when_its_monitor_leaves(self):
        settings = {
            "monitors": TWIN_SPECS,
            "workspace_rules": [{"workspace": 3, "monitor": "right"}],
        }
        events = self.run_host(
            [DELL, DELL_TWIN],
            [{"event": "monitor.removed", "monitors": [DELL], "argument": DELL_TWIN}],
            settings,
        )
        rules = [c for c in events["monitor.removed"] if c[0] != "monitor"]
        self.assertEqual(rules, [("enabled=false", "DP-4", "3", "", "")])

    # One entry for a model, two such monitors plugged in: "desc:" would let
    # Hyprland pick either, so the rule goes to the one the layout chose.
    def test_one_entry_for_two_identical_monitors_uses_the_connector(self):
        settings = {
            "monitors": [{"name": "dell", "match": "Dell Inc. DELL P2423DE"}],
            "workspace_rules": [{"workspace": 2, "monitor": "dell"}],
        }
        events = self.run_host(
            [DELL],
            [{"event": "monitor.added", "monitors": [DELL_TWIN, DELL]}],
            settings,
        )
        rules = [c for c in events["monitor.added"] if c[0] != "monitor"]
        self.assertEqual(
            rules,
            [
                ("enabled=false", "desc:Dell Inc. DELL P2423DE", "2", "", ""),
                ("workspace_rule", "DP-2", "2", "", ""),
            ],
        )


if __name__ == "__main__":
    unittest.main()
