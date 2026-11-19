"""Load the real yay init.lua against a recording stand-in for the yay API.

Each hook has an on/off switch in the environment, YAY_<HOOK NAME>, that
init.lua checks through hook_switch.lua before loading the hook: 0, off, false
or no (any case, surrounding spaces ignored) turn the hook off, any other value
or no value keeps it on. recent_update is also checked for what it does: it
holds back AUR upgrades modified less than 48 hours ago.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YAY = ROOT / "ansible/roles/dotfiles/files/home/.config/yay"
# CI installs Alpine's lua5.4, which ships only the versioned binary.
LUA = next((p for p in map(shutil.which, ("lua", "lua5.4", "luajit")) if p), "")

# Hook module -> autocmd event it registers when on.
HOOKS = {
    "orphan_check": "UpgradeSelect",
    "pkgbuild_scan": "AURPreInstall",
    "post_install": "PostInstall",
    "recent_update": "UpgradeSelect",
}
OFF_VALUES = ("0", "off", "false", "no", "OFF", "False", " off", "0\n")
ON_VALUES = ("", "1", "on", "yes", "true", "2")

# arg[1] = yay config dir, arg[2] = "upgrade" to call the UpgradeSelect
# callbacks. The fixture ages use the same os.time() clock as the hook, and sit
# far from the 48h boundary (4h, 72h); every fixture has a maintainer so
# orphan_check stays quiet.
# Prints the loaded hook modules, the registered events, the excluded packages
# and the warnings as JSON lists.
RUNNER = r"""
local dir, mode = arg[1], arg[2]
local now = os.time()
package.path = dir .. "/?.lua;" .. package.path
local events, warnings = {}, {}
yay = {
  opt = {},
  log = { warn = function(m) warnings[#warnings + 1] = m end, debug = function() end },
  create_autocmd = function(name, spec) events[#events + 1] = { name = name, spec = spec } end,
}
dofile(dir .. "/init.lua")

local excluded = {}
if mode == "upgrade" then
  local upgrades = {
    { name = "fresh-aur", repository = "aur", maintainer = "m", last_modified = now - 4 * 3600 },
    { name = "old-aur", repository = "aur", maintainer = "m", last_modified = now - 72 * 3600 },
    { name = "fresh-repo", repository = "extra", maintainer = "m", last_modified = now - 1 * 3600 },
  }
  for _, e in ipairs(events) do
    if e.name == "UpgradeSelect" then
      local result = e.spec.callback({ data = { upgrades = upgrades } })
      if result and result.exclude then
        for _, n in ipairs(result.exclude) do excluded[#excluded + 1] = n end
      end
    end
  end
end

local function list(t)
  local parts = {}
  for i, v in ipairs(t) do
    -- JSON string: escape quotes, backslashes and every control character.
    parts[i] = '"' .. v:gsub('[%c"\\]', function(c)
      return string.format("\\u%04x", c:byte())
    end) .. '"'
  end
  return "[" .. table.concat(parts, ",") .. "]"
end
local loaded, names = {}, {}
for name in pairs(package.loaded) do
  local hook = name:match("^hooks%.(.+)$")
  if hook then loaded[#loaded + 1] = hook end
end
table.sort(loaded)
for i, e in ipairs(events) do names[i] = e.name end
print(list(loaded))
print(list(names))
print(list(excluded))
print(list(warnings))
"""


def var(hook):
    return "YAY_" + hook.upper()


def run_init(switches=None, upgrade=False):
    """Run init.lua with the given YAY_* switches and nothing else set."""
    with tempfile.TemporaryDirectory() as data_home:
        env = {k: v for k, v in os.environ.items() if not k.startswith("YAY_")}
        # orphan_check reads and writes its maintainer state in XDG_DATA_HOME.
        env["XDG_DATA_HOME"] = data_home
        env.update(switches or {})
        runner = Path(data_home) / "runner.lua"
        runner.write_text(RUNNER)
        result = subprocess.run(
            [LUA, str(runner), str(YAY), "upgrade" if upgrade else ""],
            capture_output=True,
            text=True,
            env=env,
        )
    # Show the Lua error, not only the exit status.
    if result.returncode != 0:
        raise AssertionError(f"init.lua failed:\n{result.stderr}")
    out = result.stdout.splitlines()
    loaded, events, excluded, warnings = (json.loads(line) for line in out)
    return loaded, events, excluded, warnings


@unittest.skipUnless(LUA, "requires lua or luajit")
class HookSwitchTest(unittest.TestCase):
    def test_init_lists_every_hook_file(self):
        init = (YAY / "init.lua").read_text()
        listed = re.search(r"ipairs\(\{([^}]*)\}\)", init)
        self.assertIsNotNone(listed, "init.lua no longer loads hooks from a list")
        names = re.findall(r'"(\w+)"', listed.group(1))
        files = [f.stem for f in (YAY / "hooks").glob("*.lua")]
        # A new hook file must go through the switch loop, and be added here.
        self.assertCountEqual(names, files)
        self.assertCountEqual(names, HOOKS)
        self.assertNotRegex(init, r'require\("hooks\.\w+"\)')

    def test_hooks_are_on_without_variable(self):
        loaded, events, _, warnings = run_init()
        self.assertEqual(loaded, sorted(HOOKS))
        self.assertCountEqual(events, HOOKS.values())
        self.assertEqual(warnings, [])

    def test_hooks_stay_on_for_other_values(self):
        for value in ON_VALUES:
            with self.subTest(value=value):
                switches = {var(h): value for h in HOOKS}
                loaded, events, _, warnings = run_init(switches)
                self.assertEqual(loaded, sorted(HOOKS))
                self.assertCountEqual(events, HOOKS.values())
                self.assertEqual(warnings, [])

    def test_variable_turns_only_its_hook_off(self):
        for hook in HOOKS:
            others = {h: e for h, e in HOOKS.items() if h != hook}
            for value in OFF_VALUES:
                with self.subTest(hook=hook, value=value):
                    loaded, events, _, warnings = run_init({var(hook): value})
                    self.assertEqual(loaded, sorted(others))
                    self.assertCountEqual(events, others.values())
                    # Turning a check off is never silent.
                    self.assertEqual(
                        warnings,
                        [
                            f"{hook} hook disabled by {var(hook)}={value.strip().lower()}"
                        ],
                    )

    def test_all_hooks_off(self):
        loaded, events, _, warnings = run_init({var(h): "off" for h in HOOKS})
        self.assertEqual(loaded, [])
        self.assertEqual(events, [])
        self.assertEqual(len(warnings), len(HOOKS))


@unittest.skipUnless(LUA, "requires lua or luajit")
class RecentUpdateTest(unittest.TestCase):
    def test_holds_back_fresh_aur_upgrades_only(self):
        _, _, excluded, warnings = run_init(upgrade=True)
        self.assertEqual(excluded, ["fresh-aur"])
        self.assertEqual(len(warnings), 1)
        self.assertIn("fresh-aur: updated only 4h ago", warnings[0])

    def test_nothing_held_back_when_off(self):
        loaded, _, excluded, _ = run_init({var("recent_update"): "0"}, upgrade=True)
        self.assertNotIn("recent_update", loaded)
        self.assertEqual(excluded, [])


if __name__ == "__main__":
    unittest.main()
