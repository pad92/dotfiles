"""Merge of the managed Claude Code settings into ~/.claude/settings.json."""

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
DEFAULTS = yaml.safe_load(
    (ROOT / "ansible/roles/agent_cli/defaults/main.yml").read_text()
)
# A stand-in for `claude mcp remove NAME --scope user`: it logs the call and
# drops the server from the state file, as the real command does.
FAKE_CLAUDE = """#!/usr/bin/env python3
import json, sys
from pathlib import Path
Path({log!r}).open("a").write(" ".join(sys.argv[1:]) + "\\n")
state = Path({state!r})
data = json.loads(state.read_text())
data["mcpServers"].pop(sys.argv[3], None)
state.write_text(json.dumps(data))
"""


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
        self.state = self.home / ".claude.json"
        self.log = self.work / "claude.log"
        binary = self.fake_bin / FAKE_BINARY
        binary.write_text(FAKE_CLAUDE.format(log=str(self.log), state=str(self.state)))
        binary.chmod(0o755)
        self.statusline = {
            "type": "command",
            "command": f"{self.home}/.bin/claude-statusline",
        }
        self.managed = {
            "statusLine": self.statusline,
            "env": DEFAULTS["agent_cli_claude_env"],
            "enabledPlugins": DEFAULTS["agent_cli_claude_enabled_plugins"],
            "permissions": {"deny": DEFAULTS["agent_cli_claude_permissions_deny"]},
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [
                            {
                                "type": "command",
                                "command": f"{self.home}/.local/bin/rtk hook claude",
                            }
                        ],
                    }
                ]
            },
        }

    def run_play(self, *, installed=True, check=False, on_path=True, extra_vars=None):
        play = [
            {
                "hosts": "localhost",
                "connection": "local",
                "gather_facts": False,
                "vars": {
                    "agent_cli_home": str(self.home),
                    # A name absent from PATH stands for "not installed".
                    "agent_cli_claude_binary": (
                        FAKE_BINARY if installed else "claude-dotfiles-test-absent"
                    ),
                    **(extra_vars or {}),
                },
                "tasks": [
                    {
                        "ansible.builtin.import_role": {
                            "name": str(ROOT / "ansible/roles/agent_cli"),
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
        self.assertEqual(json.loads(self.settings.read_text()), self.managed)

    def test_creates_private_settings_when_absent(self):
        self.assert_succeeded(self.run_play(), changed=2)
        self.assertEqual(json.loads(self.settings.read_text()), self.managed)
        self.assertEqual(stat.S_IMODE(self.settings.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.settings.parent.stat().st_mode), 0o700)

    def test_merge_preserves_other_settings_and_is_idempotent(self):
        existing = {
            "permissions": {"allow": ["Bash(git status)"]},
            "theme": "auto",
            "autoMode": {"environment": ["Équipe — exemple"]},
        }
        self.write_settings(json.dumps(existing, ensure_ascii=False), mode=0o644)

        self.assert_succeeded(self.run_play(), changed=1)
        merged = json.loads(self.settings.read_text())
        self.assertEqual(merged["theme"], "auto")
        self.assertEqual(merged["autoMode"], existing["autoMode"])
        self.assertEqual(merged["permissions"]["allow"], ["Bash(git status)"])
        self.assertEqual(
            merged["permissions"]["deny"], self.managed["permissions"]["deny"]
        )
        self.assertEqual(merged["statusLine"], self.statusline)
        self.assertEqual(list(merged)[:3], list(existing))
        self.assertIn("Équipe — exemple", self.settings.read_text())
        self.assertEqual(stat.S_IMODE(self.settings.stat().st_mode), 0o644)

        written = self.settings.read_bytes()
        self.assert_succeeded(self.run_play(), changed=0)
        self.assertEqual(self.settings.read_bytes(), written)

    def test_merge_keeps_unmanaged_entries_of_managed_tables(self):
        otel_header = "stream-name=claude_code"
        self.write_settings(
            json.dumps(
                {
                    "env": {
                        "OTEL_EXPORTER_OTLP_HEADERS": otel_header,
                        "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "80",
                    },
                    "enabledPlugins": {"other@market": True},
                    "permissions": {"deny": ["Read(./local-only)"]},
                }
            )
        )
        self.assert_succeeded(self.run_play(), changed=1)
        merged = json.loads(self.settings.read_text())
        self.assertEqual(merged["env"]["OTEL_EXPORTER_OTLP_HEADERS"], otel_header)
        # A managed key wins over the value found on the host.
        self.assertEqual(
            merged["env"]["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"],
            DEFAULTS["agent_cli_claude_env"]["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"],
        )
        self.assertTrue(merged["enabledPlugins"]["other@market"])
        self.assertEqual(
            merged["permissions"]["deny"],
            ["Read(./local-only)", *DEFAULTS["agent_cli_claude_permissions_deny"]],
        )

    def test_deny_entries_are_not_duplicated(self):
        entry = DEFAULTS["agent_cli_claude_permissions_deny"][0]
        self.write_settings(json.dumps({"permissions": {"deny": [entry]}}))
        self.assert_succeeded(self.run_play(), changed=1)
        deny = json.loads(self.settings.read_text())["permissions"]["deny"]
        self.assertEqual(deny.count(entry), 1)

    def test_wrong_typed_managed_key_fails_without_being_overwritten(self):
        for original in (
            '{"env": ["A=1"]}',
            '{"enabledPlugins": []}',
            '{"permissions": "all"}',
            '{"permissions": {"deny": "Read(x)"}}',
        ):
            with self.subTest(original=original):
                self.write_settings(original)
                result = self.run_play()
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertEqual(self.settings.read_text(), original)
                shutil.rmtree(self.settings.parent)

    def test_removes_unwanted_user_mcp_server_once(self):
        self.state.write_text(
            json.dumps({"mcpServers": {"caveman": {}, "keep": {}}, "other": 1})
        )
        self.assert_succeeded(self.run_play(), changed=3)
        self.assertEqual(
            self.log.read_text().strip(), "mcp remove caveman --scope user"
        )
        self.assertEqual(
            json.loads(self.state.read_text()), {"mcpServers": {"keep": {}}, "other": 1}
        )
        self.assert_succeeded(self.run_play(), changed=0)
        self.assertEqual(len(self.log.read_text().splitlines()), 1)

    def test_mcp_removal_is_skipped_without_state_or_server(self):
        self.assert_succeeded(self.run_play(), changed=2)
        self.assertFalse(self.log.exists())
        self.state.write_text(json.dumps({"mcpServers": {"keep": {}}}))
        self.assert_succeeded(self.run_play(), changed=0)
        self.assertFalse(self.log.exists())

    def test_check_mode_does_not_remove_mcp_servers(self):
        self.state.write_text(json.dumps({"mcpServers": {"caveman": {}}}))
        self.run_play(check=True)
        self.assertFalse(self.log.exists())

    def test_rtk_hook_keeps_other_hooks_and_is_not_duplicated(self):
        other = {"matcher": "Edit", "hooks": [{"type": "command", "command": "fmt"}]}
        self.write_settings(
            json.dumps({"hooks": {"PreToolUse": [other], "Stop": [{"hooks": []}]}})
        )
        self.assert_succeeded(self.run_play(), changed=1)
        hooks = json.loads(self.settings.read_text())["hooks"]
        self.assertEqual(
            hooks["PreToolUse"], [other, *self.managed["hooks"]["PreToolUse"]]
        )
        self.assertEqual(hooks["Stop"], [{"hooks": []}])
        self.assert_succeeded(self.run_play(), changed=0)

    def test_rtk_hook_is_skipped_when_disabled(self):
        self.write_settings("{}")
        result = self.run_play(extra_vars={"agent_cli_rtk_enabled": False})
        self.assert_succeeded(result, changed=1)
        self.assertNotIn("hooks", json.loads(self.settings.read_text()))

    def test_wrong_typed_hooks_fail_without_being_overwritten(self):
        original = json.dumps({"hooks": {"PreToolUse": "oops"}})
        self.write_settings(original)
        result = self.run_play()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.settings.read_text(), original)

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
