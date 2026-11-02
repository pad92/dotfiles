"""Merge of the Claude Code status line into ~/.claude/settings.json."""

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from ansible_test_environment import ansible_test_environment

ROOT = Path(__file__).resolve().parents[1]
FAKE_BINARY = "claude-dotfiles-test"


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
class ClaudeSettingsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.home = self.work / "home"
        self.home.mkdir()
        self.settings = self.home / ".claude/settings.json"
        self.fake_bin = self.work / "bin"
        self.fake_bin.mkdir()
        binary = self.fake_bin / FAKE_BINARY
        binary.write_text("#!/bin/sh\nexit 0\n")
        binary.chmod(0o755)
        self.statusline = {
            "type": "command",
            "command": f"{self.home}/.bin/claude-statusline",
        }

    def run_play(self, *, installed=True, check=False, on_path=True):
        play = [
            {
                "hosts": "localhost",
                "connection": "local",
                "gather_facts": False,
                "vars": {
                    "dotfiles_home": str(self.home),
                    # A name absent from PATH stands for "not installed".
                    "dotfiles_claude_binary": (
                        FAKE_BINARY if installed else "claude-dotfiles-test-absent"
                    ),
                },
                "tasks": [
                    {
                        "ansible.builtin.import_role": {
                            "name": str(ROOT / "ansible/roles/dotfiles"),
                            "tasks_from": "claude",
                        }
                    }
                ],
            }
        ]
        playbook = self.work / "play.yml"
        playbook.write_text(yaml.safe_dump(play))
        environment = ansible_test_environment(self.work)
        if on_path:
            environment["PATH"] = f"{self.fake_bin}{os.pathsep}{environment['PATH']}"
        command = ["ansible-playbook", "-i", "localhost,", str(playbook)]
        if check:
            command.append("--check")
        return subprocess.run(
            command, env=environment, capture_output=True, text=True, check=False
        )

    def assert_succeeded(self, result, changed):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"changed={changed} ", result.stdout)

    def write_settings(self, content, mode=0o644):
        self.settings.parent.mkdir()
        self.settings.write_text(content)
        self.settings.chmod(mode)

    def test_missing_binary_creates_nothing(self):
        self.assert_succeeded(self.run_play(installed=False), changed=0)
        self.assertFalse(self.settings.parent.exists())

    def test_missing_binary_leaves_existing_settings_untouched(self):
        original = '{"theme": "auto"}\n'
        self.write_settings(original)
        self.assert_succeeded(self.run_play(installed=False), changed=0)
        self.assertEqual(self.settings.read_text(), original)

    def test_finds_binary_installed_in_local_bin(self):
        # The native installer's ~/.local/bin is often missing from PATH.
        local_bin = self.home / ".local/bin"
        local_bin.mkdir(parents=True)
        shutil.copy2(self.fake_bin / FAKE_BINARY, local_bin / FAKE_BINARY)
        self.assert_succeeded(self.run_play(on_path=False), changed=2)
        self.assertIn("statusLine", json.loads(self.settings.read_text()))

    def test_creates_private_settings_when_absent(self):
        self.assert_succeeded(self.run_play(), changed=2)
        self.assertEqual(
            json.loads(self.settings.read_text()), {"statusLine": self.statusline}
        )
        self.assertEqual(stat.S_IMODE(self.settings.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.settings.parent.stat().st_mode), 0o700)

    def test_merge_preserves_other_settings_and_is_idempotent(self):
        existing = {
            "permissions": {"allow": ["Bash(git status)"]},
            "theme": "auto",
            "autoMode": {"environment": ["Cloud Temple — CTSI2"]},
        }
        self.write_settings(json.dumps(existing, ensure_ascii=False), mode=0o644)

        self.assert_succeeded(self.run_play(), changed=1)
        merged = json.loads(self.settings.read_text())
        self.assertEqual(merged, {**existing, "statusLine": self.statusline})
        self.assertEqual(list(merged), [*existing, "statusLine"])
        self.assertIn("Cloud Temple — CTSI2", self.settings.read_text())
        self.assertEqual(stat.S_IMODE(self.settings.stat().st_mode), 0o644)

        written = self.settings.read_bytes()
        self.assert_succeeded(self.run_play(), changed=0)
        self.assertEqual(self.settings.read_bytes(), written)

    def test_replaces_a_different_status_line(self):
        self.write_settings(
            json.dumps({"statusLine": {"type": "command", "command": "old"}})
        )
        self.assert_succeeded(self.run_play(), changed=1)
        self.assertEqual(
            json.loads(self.settings.read_text())["statusLine"], self.statusline
        )

    def test_invalid_settings_fail_without_being_overwritten(self):
        for original in ("{not json", "[1, 2]"):
            with self.subTest(original=original):
                self.write_settings(original)
                result = self.run_play()
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertEqual(self.settings.read_text(), original)
                shutil.rmtree(self.settings.parent)

    def test_non_object_settings_report_an_actionable_error(self):
        self.write_settings("[1, 2]")
        result = self.run_play()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("is not a JSON object", result.stdout)

    def test_check_mode_writes_nothing(self):
        original = '{"theme": "auto"}'
        self.write_settings(original)
        self.assert_succeeded(self.run_play(check=True), changed=1)
        self.assertEqual(self.settings.read_text(), original)


if __name__ == "__main__":
    unittest.main()
