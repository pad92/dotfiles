"""Write of the Codex status line into [tui] of ~/.codex/config.toml."""

import shutil
import stat
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

import yaml
from ansible_test_environment import ansible_test_environment

ROOT = Path(__file__).resolve().parents[1]
# ini_file comes from community.general; CI installs the pinned version here
# and Ansible ignores the checkout ansible.cfg that would point to it.
COLLECTIONS = ROOT / ".ansible/collections"
FAKE_BINARY = "codex-dotfiles-test"
STATUS_LINE = ["model-with-reasoning", "context-used", "used-tokens"]
# What a real file looks like: trusted projects, a [tui] table with its own
# keys and a sub-table that Codex maintains by itself.
EXISTING = """\
# local notes
model = "gpt-5.5"

[projects."/home/user/my repo"]
trust_level = "trusted"

[tui]
screen_reader_detection_done = true

[tui.model_availability_nux]
"gpt-5.5" = 4

[features]
memories = true
"""


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
@unittest.skipUnless(COLLECTIONS.is_dir(), "requires pinned Ansible collections")
class CodexConfigTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.home = self.work / "home"
        self.home.mkdir()
        self.config = self.home / ".codex/config.toml"
        self.fake_bin = self.work / "bin"
        self.fake_bin.mkdir()
        binary = self.fake_bin / FAKE_BINARY
        binary.write_text("#!/bin/sh\nexit 0\n")
        binary.chmod(0o755)

    def run_play(self, *, installed=True, check=False, status_line=None):
        play = [
            {
                "hosts": "localhost",
                "connection": "local",
                "gather_facts": False,
                "vars": {
                    "dotfiles_home": str(self.home),
                    "dotfiles_codex_binary": (
                        FAKE_BINARY if installed else "codex-dotfiles-test-absent"
                    ),
                    "dotfiles_codex_status_line": (
                        STATUS_LINE if status_line is None else status_line
                    ),
                },
                "tasks": [
                    {
                        "ansible.builtin.import_role": {
                            "name": str(ROOT / "ansible/roles/dotfiles"),
                            "tasks_from": "codex",
                        }
                    }
                ],
            }
        ]
        playbook = self.work / "play.yml"
        playbook.write_text(yaml.safe_dump(play))
        environment = ansible_test_environment(self.work)
        environment["PATH"] = f"{self.fake_bin}:{environment['PATH']}"
        environment["ANSIBLE_COLLECTIONS_PATH"] = str(COLLECTIONS)
        command = ["ansible-playbook", "-i", "localhost,", str(playbook)]
        if check:
            command.append("--check")
        return subprocess.run(
            command, env=environment, capture_output=True, text=True, check=False
        )

    def assert_succeeded(self, result, changed):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"changed={changed} ", result.stdout)

    def write_config(self, content, mode=0o600):
        self.config.parent.mkdir()
        self.config.write_text(content)
        self.config.chmod(mode)

    def loaded(self):
        return tomllib.loads(self.config.read_text())

    def test_missing_binary_creates_nothing(self):
        self.assert_succeeded(self.run_play(installed=False), changed=0)
        self.assertFalse(self.config.parent.exists())

    def test_missing_binary_leaves_existing_config_untouched(self):
        self.write_config(EXISTING)
        self.assert_succeeded(self.run_play(installed=False), changed=0)
        self.assertEqual(self.config.read_text(), EXISTING)

    def test_creates_private_config_when_absent(self):
        self.assert_succeeded(self.run_play(), changed=2)
        self.assertEqual(self.loaded(), {"tui": {"status_line": STATUS_LINE}})
        self.assertEqual(stat.S_IMODE(self.config.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.config.parent.stat().st_mode), 0o700)

    def test_write_preserves_everything_else_and_is_idempotent(self):
        self.write_config(EXISTING, mode=0o640)
        before = tomllib.loads(EXISTING)

        self.assert_succeeded(self.run_play(), changed=1)
        after = self.loaded()
        self.assertEqual(after["tui"].pop("status_line"), STATUS_LINE)
        self.assertEqual(after, before)
        # Every original line survives, comment included: only one is added.
        written = self.config.read_text().splitlines()
        self.assertEqual(
            [line for line in written if not line.startswith("status_line")],
            EXISTING.splitlines(),
        )
        self.assertEqual(stat.S_IMODE(self.config.stat().st_mode), 0o640)

        content = self.config.read_bytes()
        self.assert_succeeded(self.run_play(), changed=0)
        self.assertEqual(self.config.read_bytes(), content)

    def test_adds_the_tui_table_when_only_its_sub_table_exists(self):
        self.write_config('[tui.model_availability_nux]\n"gpt-5.5" = 4\n')
        self.assert_succeeded(self.run_play(), changed=1)
        self.assertEqual(
            self.loaded()["tui"],
            {"model_availability_nux": {"gpt-5.5": 4}, "status_line": STATUS_LINE},
        )

    def test_replaces_a_different_status_line(self):
        self.write_config('[tui]\nstatus_line = ["git-branch"]\ntheme = "dark"\n')
        self.assert_succeeded(self.run_play(), changed=1)
        self.assertEqual(
            self.loaded()["tui"], {"status_line": STATUS_LINE, "theme": "dark"}
        )

    def test_same_value_in_another_layout_is_not_a_change(self):
        # Codex may rewrite the array on several lines.
        original = (
            "[tui]\nstatus_line = [\n"
            + "".join(f'  "{item}",\n' for item in STATUS_LINE)
            + "]\n"
        )
        self.write_config(original)
        self.assert_succeeded(self.run_play(), changed=0)
        self.assertEqual(self.config.read_text(), original)

    def test_unwritable_layouts_fail_and_restore_the_file(self):
        # A one-line edit would corrupt both: a multi-line array keeps its
        # tail, and a dotted key outside [tui] becomes a duplicate.
        originals = {
            "multi-line array": '[tui]\nstatus_line = [\n  "git-branch",\n]\n',
            "dotted root key": 'tui.status_line = ["git-branch"]\nmodel = "x"\n',
        }
        for name, original in originals.items():
            with self.subTest(layout=name):
                shutil.rmtree(self.config.parent, ignore_errors=True)
                self.write_config(original, mode=0o640)
                result = self.run_play()
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("the file was restored", result.stdout)
                self.assertEqual(self.config.read_text(), original)
                self.assertEqual(stat.S_IMODE(self.config.stat().st_mode), 0o640)

    def test_invalid_config_fails_without_being_overwritten(self):
        for original in ("[tui\n", "tui = 3\n"):
            with self.subTest(original=original):
                shutil.rmtree(self.config.parent, ignore_errors=True)
                self.write_config(original)
                result = self.run_play()
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("is not valid TOML", result.stdout)
                self.assertEqual(self.config.read_text(), original)

    def test_identifiers_needing_toml_escaping_are_refused(self):
        self.write_config(EXISTING)
        for status_line in (['bad"quote'], [], "context-used"):
            with self.subTest(status_line=status_line):
                result = self.run_play(status_line=status_line)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("must be a non-empty list", result.stdout)
                self.assertEqual(self.config.read_text(), EXISTING)

    def test_check_mode_writes_nothing(self):
        self.write_config(EXISTING)
        self.assert_succeeded(self.run_play(check=True), changed=1)
        self.assertEqual(self.config.read_text(), EXISTING)

    def test_default_identifiers_exist_in_the_installed_codex(self):
        # An unknown identifier is dropped by Codex with a warning at startup.
        codex = shutil.which("codex")
        if codex is None:
            self.skipTest("requires codex")
        defaults = yaml.safe_load(
            (ROOT / "ansible/roles/dotfiles/defaults/main.yml").read_text()
        )
        binary = Path(codex).read_bytes()
        for item in defaults["dotfiles_codex_status_line"]:
            with self.subTest(item=item):
                self.assertIn(item.encode(), binary)


if __name__ == "__main__":
    unittest.main()
