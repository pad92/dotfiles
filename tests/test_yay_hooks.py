"""Run the yay Lua hooks against a recording stand-in for the yay API.

Each hook has an on/off switch in the environment, YAY_<HOOK NAME>, read by
hook_switch.lua: 0, off, false or no turn the hook off, any other value or no
value keeps it on. recent_update is also checked for what it does: it holds
back AUR upgrades modified less than 48 hours ago.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YAY = ROOT / "ansible/roles/dotfiles/files/home/.config/yay"
LUA = shutil.which("lua") or shutil.which("luajit") or ""

# Hook module -> autocmd event it registers when on.
HOOKS = {
    "orphan_check": "UpgradeSelect",
    "pkgbuild_scan": "AURPreInstall",
    "post_install": "PostInstall",
    "recent_update": "UpgradeSelect",
}
OFF_VALUES = ("0", "off", "false", "no", "OFF", "False")
ON_VALUES = ("", "1", "on", "yes", "true", "2")

# arg[1] = yay config dir, arg[2] = hook module, arg[3] = os.time() of the
# fixture, arg[4] = "upgrade" to call the UpgradeSelect callbacks.
# Prints the registered events, the excluded packages and the warnings as JSON.
RUNNER = r"""
local dir, hook, now, mode = arg[1], arg[2], tonumber(arg[3]), arg[4]
package.path = dir .. "/?.lua;" .. package.path
local events, warnings = {}, {}
yay = {
  log = { warn = function(m) warnings[#warnings + 1] = m end, debug = function() end },
  create_autocmd = function(name, spec) events[#events + 1] = { name = name, spec = spec } end,
}
require("hooks." .. hook)

local excluded = {}
if mode == "upgrade" then
  local upgrades = {
    { name = "fresh-aur", repository = "aur", last_modified = now - 4 * 3600 },
    { name = "old-aur", repository = "aur", last_modified = now - 72 * 3600 },
    { name = "fresh-repo", repository = "extra", last_modified = now - 1 * 3600 },
  }
  for _, e in ipairs(events) do
    local result = e.spec.callback({ data = { upgrades = upgrades } })
    if result and result.exclude then
      for _, n in ipairs(result.exclude) do excluded[#excluded + 1] = n end
    end
  end
end

local function list(t)
  local parts = {}
  for i, v in ipairs(t) do parts[i] = string.format("%q", v) end
  return "[" .. table.concat(parts, ",") .. "]"
end
local names = {}
for i, e in ipairs(events) do names[i] = e.name end
print(list(names))
print(list(excluded))
print(list(warnings))
"""


def run_hook(hook, env_value, upgrade=False, extra_env=None):
    var = "YAY_" + hook.upper()
    with tempfile.TemporaryDirectory() as data_home:
        env = {k: v for k, v in os.environ.items() if not k.startswith("YAY_")}
        # orphan_check reads its maintainer state from XDG_DATA_HOME at load.
        env["XDG_DATA_HOME"] = data_home
        env.update(extra_env or {})
        if env_value is not None:
            env[var] = env_value
        # os.time() inside the hook and the fixture timestamps share one clock;
        # the fixture ages (4h, 72h) are far from the 48h boundary.
        now = subprocess.run(
            [LUA, "-e", "print(os.time())"], capture_output=True, text=True, check=True
        ).stdout.strip()
        runner = Path(data_home) / "runner.lua"
        runner.write_text(RUNNER)
        out = subprocess.run(
            [LUA, str(runner), str(YAY), hook, now, "upgrade" if upgrade else ""],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        ).stdout.splitlines()
    events, excluded, warnings = (json.loads(line) for line in out)
    return events, excluded, warnings


@unittest.skipUnless(LUA, "requires lua or luajit")
class HookSwitchTest(unittest.TestCase):
    def test_every_hook_in_init_has_a_switch(self):
        init = (YAY / "init.lua").read_text()
        for hook in HOOKS:
            self.assertIn(f'require("hooks.{hook}")', init)
            source = (YAY / "hooks" / f"{hook}.lua").read_text()
            self.assertIn(f'require("hook_switch").disabled("{hook}")', source)

    def test_hooks_are_on_without_variable(self):
        for hook, event in HOOKS.items():
            with self.subTest(hook=hook):
                events, _, warnings = run_hook(hook, None)
                self.assertEqual(events, [event])
                self.assertEqual(warnings, [])

    def test_hooks_stay_on_for_other_values(self):
        for hook, event in HOOKS.items():
            for value in ON_VALUES:
                with self.subTest(hook=hook, value=value):
                    events, _, warnings = run_hook(hook, value)
                    self.assertEqual(events, [event])
                    self.assertEqual(warnings, [])

    def test_variable_turns_hook_off(self):
        for hook in HOOKS:
            var = "YAY_" + hook.upper()
            for value in OFF_VALUES:
                with self.subTest(hook=hook, value=value):
                    events, _, warnings = run_hook(hook, value)
                    self.assertEqual(events, [])
                    # Turning a check off is never silent.
                    self.assertEqual(
                        warnings, [f"{hook} hook disabled by {var}={value.lower()}"]
                    )

    def test_switch_only_affects_its_own_hook(self):
        for hook, event in HOOKS.items():
            others_off = {"YAY_" + h.upper(): "0" for h in HOOKS if h != hook}
            with self.subTest(hook=hook):
                events, _, warnings = run_hook(hook, None, extra_env=others_off)
                self.assertEqual(events, [event])
                self.assertEqual(warnings, [])


@unittest.skipUnless(LUA, "requires lua or luajit")
class RecentUpdateTest(unittest.TestCase):
    def test_holds_back_fresh_aur_upgrades_only(self):
        events, excluded, warnings = run_hook("recent_update", None, upgrade=True)
        self.assertEqual(events, ["UpgradeSelect"])
        self.assertEqual(excluded, ["fresh-aur"])
        self.assertEqual(len(warnings), 1)
        self.assertIn("fresh-aur: updated only 4h ago", warnings[0])

    def test_nothing_held_back_when_off(self):
        events, excluded, _ = run_hook("recent_update", "0", upgrade=True)
        self.assertEqual(events, [])
        self.assertEqual(excluded, [])


if __name__ == "__main__":
    unittest.main()
