"""Render the host-dependent dotfiles from the real group_vars of each machine."""

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from ansible_host_profiles import inventory_arguments
from ansible_test_environment import ansible_test_environment

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "ansible/roles/dotfiles"
RENDERED = {
    "home/.config/hypr/hypridle.conf.j2": "hypridle.conf",
    "home/.config/hypr/hosts/settings.lua.j2": "settings.lua",
    "home/.config/waybar/config.j2": "waybar.json",
    "home/.config/waybar/conf/temperature.json.j2": "temperature.json",
}
VAULT = {
    "vault_dotfiles_monitor_outputs": {
        "dell": "desc:Dell Fixture DELL-SERIAL",
        "asus": "desc:ASUS Fixture ASUS-SERIAL",
    }
}
LUA = shutil.which("lua") or shutil.which("luajit")
# Runs include/host.lua against a recording stand-in for Hyprland's hl API.
LUA_HARNESS = """
package.path = arg[1] .. "/?.lua;" .. package.path
local calls = {}
local function record(kind)
  return function(value) table.insert(calls, { kind = kind, value = value }) end
end
_G.hl = {
  monitor = record("monitor"),
  workspace_rule = record("workspace_rule"),
  window_rule = record("window_rule"),
  config = record("config"),
}
local messages, loaded = require("include.host").load()
print(tostring(loaded) .. " " .. table.concat(messages, "|"))
for _, call in ipairs(calls) do
  local value = call.value
  print(call.kind, value.output or value.monitor or "",
    value.mode or value.workspace or "",
    value.position or "",
    value.input and value.input.touchdevice.output or "",
    value.decoration and tostring(value.decoration.blur.enabled) or "")
end
"""


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
class HostTemplateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)

    def run_play(self, hostname, form_factor, extra_vars=None, check=True):
        """Render the templates as the role would for a hostname and chassis."""
        output = self.work / hostname
        output.mkdir(exist_ok=True)
        play = [
            {
                "hosts": hostname,
                "gather_facts": False,
                "vars": {
                    "ansible_facts": {
                        "hostname": hostname,
                        "form_factor": form_factor,
                        "user_id": "demo",
                        "user_gid": 1000,
                    },
                    "dotfiles_home": str(self.work / "home"),
                },
                "tasks": [
                    {
                        "ansible.builtin.import_role": {
                            "name": str(ROLE),
                            "tasks_from": "validate",
                        }
                    },
                    {
                        "ansible.builtin.template": {
                            "src": str(ROLE / "templates" / "{{ item.key }}"),
                            "dest": str(output / "{{ item.value }}"),
                            "mode": "0600",
                        },
                        "loop": "{{ rendered | dict2items }}",
                        "vars": {"rendered": RENDERED},
                    },
                ],
            }
        ]
        playbook = self.work / f"play-{hostname}.yml"
        playbook.write_text(yaml.safe_dump(play))
        command = ["ansible-playbook", *inventory_arguments(hostname), str(playbook)]
        if extra_vars:
            command += ["-e", json.dumps(extra_vars)]
        result = subprocess.run(
            command,
            cwd=self.work,
            env=ansible_test_environment(self.work),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if check:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return output, result

    def rendered(self, output):
        waybar = json.loads((output / "waybar.json").read_text())
        temperature = json.loads((output / "temperature.json").read_text())
        return (
            waybar,
            temperature,
            (output / "hypridle.conf").read_text(),
            (output / "settings.lua").read_text(),
        )

    def hyprland_calls(self, settings_file):
        """Load the rendered settings through the shipped include/host.lua."""
        config = self.work / "hypr"
        shutil.copytree(ROLE / "files/home/.config/hypr/include", config / "include")
        (config / "hosts").mkdir()
        shutil.copy(settings_file, config / "hosts/settings.lua")
        result = subprocess.run(
            [LUA, "-", str(config)],
            input=LUA_HARNESS,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        shutil.rmtree(config)
        status, *calls = result.stdout.splitlines()
        return status, [line.split("\t") for line in calls]

    def test_desktop_suspends_and_routes_games_without_battery_modules(self):
        output, _ = self.run_play("PadsTower", "Desktop", VAULT)
        waybar, temperature, hypridle, settings = self.rendered(output)
        modules = waybar["modules-right"]
        self.assertNotIn("battery", modules)
        self.assertNotIn("backlight", modules)
        self.assertLess(modules.index("temperature#cpu"), modules.index("memory"))
        self.assertIn("~/.config/waybar/conf/temperature.json", waybar["include"])
        self.assertEqual(
            temperature["temperature#cpu"]["hwmon-path-abs"],
            "/sys/devices/pci0000:00/0000:00:18.3/hwmon",
        )
        self.assertEqual(temperature["temperature#gpu"]["tooltip-format"][:4], "GPU:")
        self.assertRegex(
            hypridle,
            r"timeout = 3600\n\s+on-timeout = ~/.bin/hyprlock-carousel-suspend.sh",
        )
        self.assertNotIn("is-host", hypridle)
        self.assertIn('"desc:ASUS Fixture ASUS-SERIAL"', settings)
        self.assertIn('"2560x1440@144"', settings)
        self.assertIn("steam_app_", settings)
        if LUA:
            status, calls = self.hyprland_calls(output / "settings.lua")
            self.assertEqual(status, "true Host settings loaded")
            kinds = [call[0] for call in calls]
            self.assertEqual(kinds.count("monitor"), 2)
            self.assertEqual(kinds.count("window_rule"), 2)
            # A desktop keeps the blur and shadows of conf/appearance.lua.
            self.assertNotIn("config", kinds)

    def test_laptop_shows_battery_and_saves_power_without_suspending(self):
        output, _ = self.run_play("PadsP5560", "Notebook", VAULT)
        waybar, temperature, hypridle, settings = self.rendered(output)
        modules = waybar["modules-right"]
        self.assertEqual(
            modules[modules.index("temperature#gpu") + 1 :][:3],
            ["backlight", "battery", "custom/lact-profile"],
        )
        self.assertEqual(
            temperature["temperature#gpu"]["input-filename"], "temp12_input"
        )
        self.assertNotIn("suspend", hypridle)
        self.assertIn('"2560x1440@60"', settings)
        self.assertNotIn("steam", settings)
        if LUA:
            status, calls = self.hyprland_calls(output / "settings.lua")
            self.assertEqual(status, "true Host settings loaded")
            monitors = [
                (call[1], call[2], call[3]) for call in calls if call[0] == "monitor"
            ]
            self.assertEqual(
                monitors,
                [
                    ("desc:Sharp Corporation 0x1516", "3840x2400", "0x1440"),
                    ("desc:ASUS Fixture ASUS-SERIAL", "2560x1440@60", "2560x0"),
                    ("desc:Dell Fixture DELL-SERIAL", "2560x1440", "0x0"),
                ],
            )
            workspaces = [call[2] for call in calls if call[0] == "workspace_rule"]
            self.assertEqual(workspaces, ["1", "2", "8"])
            self.assertIn(["config", "", "", "", "eDP-1", "false"], calls)

    # Without the Vault the serial-bearing outputs are unknown: their monitors
    # and every rule that targets them are left out instead of half-applied.
    def test_missing_vault_leaves_external_monitors_to_the_generic_rule(self):
        output, _ = self.run_play("PadsTower", "Desktop")
        settings = (output / "settings.lua").read_text()
        self.assertIn("monitors = {}", settings)
        self.assertIn("workspace_rules = {}", settings)
        self.assertIn("window_rules = {}", settings)

    def test_unknown_host_gets_generic_files(self):
        output, _ = self.run_play("fresh-box", "Laptop")
        waybar, temperature, hypridle, _ = self.rendered(output)
        self.assertEqual(temperature, {})
        self.assertFalse(
            [module for module in waybar["modules-right"] if "temperature" in module]
        )
        self.assertIn("battery", waybar["modules-right"])
        self.assertNotIn("suspend", hypridle)

    def test_invalid_settings_fail_before_rendering(self):
        cases = {
            "sensor outside /sys": {
                "dotfiles_waybar_temperature_sensors": [
                    {
                        "name": "cpu",
                        "label": "CPU",
                        "hwmon_path": "/sys/../etc",
                        "input_filename": "temp1_input",
                    }
                ]
            },
            "monitor without mode": {
                "dotfiles_hypr_monitors": [{"output": "DP-1", "position": "0x0"}]
            },
            "unquoted position": {
                "dotfiles_hypr_monitors": [
                    {"output": "DP-1", "mode": "1920x1080", "position": 0, "scale": 1}
                ]
            },
            "sensor without label": {
                "dotfiles_waybar_temperature_sensors": [
                    {
                        "name": "cpu",
                        "hwmon_path": "/sys/class/hwmon",
                        "input_filename": "temp1_input",
                    }
                ]
            },
            "negative timeout": {"dotfiles_hypridle_suspend_timeout": -1},
            "relative home": {"dotfiles_home": "relative/home"},
        }
        for name, extra_vars in cases.items():
            with self.subTest(case=name):
                output, result = self.run_play(
                    "PadsTower", "Desktop", extra_vars, False
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Invalid dotfiles settings", result.stdout)
                self.assertFalse(any(output.iterdir()))

    # Host decisions belong to Ansible variables, not to the rendered files.
    def test_templates_do_not_branch_on_the_host_name(self):
        pattern = re.compile(r"inventory_hostname|ansible_hostname|\['hostname'\]")
        for template in sorted((ROLE / "templates").rglob("*.j2")):
            with self.subTest(template=template.relative_to(ROLE).as_posix()):
                self.assertIsNone(pattern.search(template.read_text()))
        self.assertFalse(list((ROLE / "files/home/.config/hypr/hosts").glob("*")))


if __name__ == "__main__":
    unittest.main()
