"""Exercise the LACT tooltip and its existing click action without services."""

import runpy
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "ansible/roles/dotfiles/files/home/.config/waybar/modules/lact-profile"
API = runpy.run_path(str(MODULE))


class LactTooltipTests(unittest.TestCase):
    def run_query(self, arguments, **kwargs):
        if arguments == ["lact", "cli", "profile", "list"]:
            output = "Default\nBalance\nSilence\nJeux-perf\n"
        elif arguments == ["lact", "cli", "profile", "get"]:
            output = "Balance\n"
        elif arguments == ["powerprofilesctl", "get"]:
            output = "balanced\n"
        else:
            output = "LoadState=loaded\nActiveState=active\nSubState=running\n"
        return subprocess.CompletedProcess(arguments, 0, output, "")

    def test_services_only_appear_in_tooltip(self):
        with patch("subprocess.run", side_effect=self.run_query):
            result = API["status"]()
        self.assertEqual(result["class"], "balance")
        self.assertNotIn("balanced", result["text"])
        self.assertIn("LACT : Balance", result["tooltip"])
        self.assertIn("Profil d’énergie : balanced", result["tooltip"])
        self.assertIn("ananicy-cpp : active (running)", result["tooltip"])

    def test_missing_and_failed_services_remain_readable(self):
        for output, expected in [
            ("LoadState=not-found", "non installé"),
            (
                "LoadState=loaded\nActiveState=failed\nSubState=failed",
                "failed (failed)",
            ),
        ]:
            with patch(
                "subprocess.run",
                return_value=subprocess.CompletedProcess([], 0, output, ""),
            ):
                self.assertIn(expected, API["service_status"]("ananicy-cpp"))

    def test_service_errors_are_escaped_without_hiding_lact(self):
        def query(arguments, **kwargs):
            if arguments[0] == "systemctl":
                raise subprocess.CalledProcessError(1, arguments, stderr="<bus error>")
            return self.run_query(arguments, **kwargs)

        with patch("subprocess.run", side_effect=query):
            result = API["status"]()
        self.assertEqual(result["class"], "balance")
        self.assertIn("&lt;bus error&gt;", result["tooltip"])

    def test_unavailable_lact_hides_the_indicator(self):
        with patch("subprocess.run", side_effect=FileNotFoundError("lact")):
            self.assertEqual(API["status"](), {"text": ""})

    def test_click_only_changes_lact(self):
        with patch("subprocess.run", side_effect=self.run_query) as run:
            API["cycle_profile"]()
        self.assertEqual(
            run.call_args.args[0], ["lact", "cli", "profile", "set", "Silence"]
        )
        self.assertTrue(all(call.args[0][0] == "lact" for call in run.call_args_list))
