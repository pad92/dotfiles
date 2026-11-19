"""Check the Waybar tooltips that are plain configuration or small scripts."""

import json
import runpy
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
WAYBAR = ROOT / "ansible/roles/dotfiles/files/home/.config/waybar"
HEADSET = runpy.run_path(str(WAYBAR / "modules/headsetcontrol"))
VPN = runpy.run_path(str(WAYBAR / "modules/vpn"))
RECORD = ROOT / "ansible/roles/dotfiles/files/home/.bin/hypr-record.sh"
TEMPERATURE = (
    ROOT
    / "ansible/roles/dotfiles/templates/home/.config/waybar/conf/temperature.json.j2"
)
# Sample values for the placeholders the configured tooltips use; Waybar
# formats them with fmt, whose replacement syntax str.format shares.
PLACEHOLDERS = {
    "avg_frequency": 2.4,
    "calendar": "",
    "capacity": 80,
    "controller_alias": "hci0",
    "desc": "Headset",
    "device_alias": "Keyboard",
    "device_battery_percentage": 50,
    "device_enumerate": "",
    "load": 1.5,
    "num_connections": 1,
    "percent": 40,
    "percentage": 30,
    "power": 7.25,
    "status": "on",
    "swapTotal": 8.0,
    "swapUsed": 0.0,
    "time": "2 h 10 min",
    "total": 31.2,
    "usage": 12,
    "used": 9.8,
    "volume": 35,
}


def config(name: str) -> dict:
    return json.loads((WAYBAR / "conf" / name).read_text(encoding="utf-8"))


def tooltips() -> dict[str, str]:
    """Every tooltip format of the static configuration, by module and key."""
    found = {}
    for path in sorted((WAYBAR / "conf").glob("*.json")):
        for module, settings in json.loads(path.read_text(encoding="utf-8")).items():
            for key, value in settings.items():
                if key.startswith("tooltip-format"):
                    found[f"{module} {key}"] = value
    return found


def assert_convention(case: unittest.TestCase, tooltip: str, label: str) -> None:
    """'Name: state' first, then details, then one line per click, last."""
    lines = tooltip.split("\n")
    case.assertRegex(lines[0], r"^[^\n]*\S: ", label)
    case.assertNotRegex(tooltip, r" : |— click|click to", label)
    clicks = [
        i for i, line in enumerate(lines) if line.startswith(("click", "right-click"))
    ]
    case.assertEqual(clicks, list(range(len(lines) - len(clicks), len(lines))), label)
    for index in clicks:
        case.assertRegex(lines[index], r"^(right-)?click: \S", label)


def headset_report(battery: dict, product: str = "HS70 <Pro> & Co") -> str:
    return json.dumps({"devices": [{"product": product, "battery": battery}]})


class ConventionTests(unittest.TestCase):
    def test_static_tooltips_follow_the_convention_and_format(self):
        for label, tooltip in tooltips().items():
            if "{calendar}" in tooltip or "enumerate" in label:
                continue
            assert_convention(self, tooltip, label)
            tooltip.format(**PLACEHOLDERS)

    def test_builtin_modules_replace_waybar_defaults(self):
        found = tooltips()
        for module in ("cpu", "memory", "battery", "backlight"):
            self.assertIn(f"{module} tooltip-format", found)
        self.assertIn("time left", found["battery tooltip-format-discharging"])
        self.assertIn(": {temperatureC}°C", TEMPERATURE.read_text(encoding="utf-8"))

    def test_bar_text_is_english_only(self):
        """No French label is left in the bar, its scripts or the clock."""
        sources = [*WAYBAR.rglob("*"), TEMPERATURE, RECORD]
        for path in (path for path in sources if path.is_file()):
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"[àâçéèêëîïôûùœ]|\bclic\b", path)
        self.assertEqual(config("system.json")["clock"]["locale"], "en_US.UTF-8")

    def test_vpn_states_follow_the_convention(self):
        for css_class, tooltip in [*VPN["STATES"].values(), VPN["DISCONNECTED"]]:
            assert_convention(self, tooltip, css_class)
        self.assertNotIn("click", VPN["STATES"]["deactivating"][1])


class BluetoothTooltipTests(unittest.TestCase):
    def test_off_and_disabled_do_not_fall_back_to_a_connection_count(self):
        bluetooth = config("connectivity.json")["bluetooth"]
        self.assertIn(": off", bluetooth["tooltip-format-off"])
        self.assertIn("disabled", bluetooth["tooltip-format-disabled"])
        self.assertNotIn("connected", bluetooth["tooltip-format"])

    def test_no_hardware_address_is_shown(self):
        bluetooth = config("connectivity.json")["bluetooth"]
        for key, value in bluetooth.items():
            if key.startswith("tooltip"):
                self.assertNotIn("_address}", value, key)


class AudioTooltipTests(unittest.TestCase):
    def test_sink_tooltip_names_both_click_actions(self):
        pulseaudio = config("audio.json")["pulseaudio"]
        self.assertIn("cycle-default-sink", pulseaudio["on-click"])
        self.assertTrue(
            pulseaudio["tooltip-format"].endswith(
                "\nclick: next output\nright-click: pavucontrol"
            )
        )

    def test_headset_module_reads_json_with_a_tooltip(self):
        headset = config("audio.json")["custom/headsetcontrol"]
        self.assertEqual(headset["return-type"], "json")
        self.assertTrue(headset["tooltip"])


class HeadsetTooltipTests(unittest.TestCase):
    def run_headset(self, stdout: str):
        completed = subprocess.CompletedProcess([], 0, stdout, "")
        with patch("subprocess.run", return_value=completed):
            return HEADSET["status"]()

    def test_charging_level_names_the_device_and_the_read_time(self):
        result = self.run_headset(
            headset_report({"status": "BATTERY_CHARGING", "level": 42})
        )
        self.assertEqual(result["text"], "HS 42%")
        self.assertEqual(result["class"], "charging")
        self.assertRegex(
            result["tooltip"],
            r"^HS70 &lt;Pro&gt; &amp; Co: 42% \(charging\)\nread at \d\d:\d\d$",
        )

    def test_offline_headset_hides_the_module(self):
        result = self.run_headset(
            headset_report({"status": "BATTERY_UNAVAILABLE", "level": -1})
        )
        self.assertEqual(result, {"text": ""})

    def test_missing_tool_or_bad_output_hides_the_module(self):
        with patch("subprocess.run", side_effect=FileNotFoundError("headsetcontrol")):
            self.assertEqual(HEADSET["status"](), {"text": ""})
        self.assertEqual(self.run_headset("not json"), {"text": ""})
        self.assertEqual(self.run_headset("[]"), {"text": ""})


if __name__ == "__main__":
    unittest.main()
