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


def config(name: str) -> dict:
    return json.loads((WAYBAR / "conf" / name).read_text(encoding="utf-8"))


def headset_report(battery: dict, product: str = "HS70 <Pro> & Co") -> str:
    return json.dumps({"devices": [{"product": product, "battery": battery}]})


class BluetoothTooltipTests(unittest.TestCase):
    def test_off_and_disabled_do_not_fall_back_to_a_connection_count(self):
        bluetooth = config("connectivity.json")["bluetooth"]
        self.assertIn("éteint", bluetooth["tooltip-format-off"])
        self.assertIn("désactivé", bluetooth["tooltip-format-disabled"])
        self.assertNotIn("connecté", bluetooth["tooltip-format"])

    def test_no_hardware_address_is_shown(self):
        bluetooth = config("connectivity.json")["bluetooth"]
        for key, value in bluetooth.items():
            if key.startswith("tooltip"):
                self.assertNotIn("_address}", value, key)


class AudioTooltipTests(unittest.TestCase):
    def test_sink_tooltip_names_both_click_actions(self):
        pulseaudio = config("audio.json")["pulseaudio"]
        self.assertIn("cycle-default-sink", pulseaudio["on-click"])
        self.assertIn("sortie suivante", pulseaudio["tooltip-format"])
        self.assertIn("pavucontrol", pulseaudio["tooltip-format"])

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
        self.assertIn("HS70 &lt;Pro&gt; &amp; Co", result["tooltip"])
        self.assertIn("Batterie : 42 % (en charge)", result["tooltip"])
        self.assertRegex(result["tooltip"], r"lu à \d\d:\d\d")

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
