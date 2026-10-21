"""Exercise the real Ansible policy tasks against simulated CPU controls."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "ansible/roles/system/tasks/amd_epp_policy.yml"


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
class AmdEppPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.policy = self.directory / "policy0"
        self.policy.mkdir()
        for name, content in {
            "scaling_governor": "performance",
            "scaling_available_governors": "performance powersave",
            "energy_performance_preference": "performance",
            "energy_performance_available_preferences": "performance",
        }.items():
            (self.policy / name).write_text(content + "\n")
        binary = self.directory / "bin"
        binary.mkdir()
        self.available_preferences = self.directory / "available-preferences"
        self.available_preferences.write_text("performance balance_performance power\n")
        tee = binary / "tee"
        tee.write_text("""#!/usr/bin/env python3
import sys
from pathlib import Path
path = Path(sys.argv[1])
value = sys.stdin.read()
if path.name == "energy_performance_preference":
    failure = path.parent / "reject-epp-once"
    if failure.exists():
        failure.unlink()
        path.write_text("power\\n")
        sys.exit("Simulated EPP write failure")
    if (path.parent / "scaling_governor").read_text().strip() != "powersave":
        sys.exit("EPP requires powersave")
else:
    # Simulate governor-dependent EPP choices and a preference reset.
    choices = Path(__file__).resolve().parents[1] / "available-preferences"
    (path.parent / "energy_performance_available_preferences").write_text(
        choices.read_text() if value.strip() == "powersave" else "performance\\n"
    )
    (path.parent / "energy_performance_preference").write_text("performance\\n")
path.write_text(value)
print(value, end="")
""")
        tee.chmod(0o755)
        self.playbook = self.directory / "play.yml"
        self.playbook.write_text(
            yaml.safe_dump(
                [
                    {
                        "hosts": "localhost",
                        "gather_facts": False,
                        "connection": "local",
                        "environment": {"PATH": f"{binary}:{os.environ['PATH']}"},
                        "vars": {
                            "system_amd_policy": {
                                "path": str(
                                    self.policy / "energy_performance_preference"
                                ),
                            },
                            "system_amd_pstate_epp": "balance_performance",
                        },
                        "tasks": [{"ansible.builtin.include_tasks": str(TASKS)}],
                    }
                ]
            )
        )

    def run_play(self, *arguments):
        return subprocess.run(
            ["ansible-playbook", "-i", "localhost,", str(self.playbook), *arguments],
            cwd=ROOT,
            env={**os.environ, "ANSIBLE_LOCAL_TEMP": str(self.directory / "ansible")},
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )

    def snapshot(self):
        return {path.name: path.read_text() for path in self.policy.iterdir()}

    def test_governor_precedes_epp_and_second_run_is_unchanged(self):
        first = self.run_play()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(
            (self.policy / "scaling_governor").read_text().strip(), "powersave"
        )
        self.assertEqual(
            (self.policy / "energy_performance_preference").read_text().strip(),
            "balance_performance",
        )
        second = self.run_play()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertRegex(second.stdout, r"changed=0\b")

    def test_check_mode_does_not_write_cpu_controls(self):
        before = self.snapshot()
        result = self.run_play("--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_unsupported_preference_restores_original_governor(self):
        self.available_preferences.write_text("performance\n")
        before = self.snapshot()
        result = self.run_play()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Could not configure", result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_failed_epp_write_restores_governor_and_preference(self):
        before = self.snapshot()
        (self.policy / "reject-epp-once").touch()
        result = self.run_play()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Simulated EPP write failure", result.stdout)
        self.assertIn("original governor and EPP were restored", result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_failed_epp_write_restores_preference_when_already_powersave(self):
        (self.policy / "scaling_governor").write_text("powersave\n")
        (self.policy / "energy_performance_preference").write_text("balance_power\n")
        (self.policy / "energy_performance_available_preferences").write_text(
            "performance balance_performance balance_power power\n"
        )
        before = self.snapshot()
        (self.policy / "reject-epp-once").touch()
        result = self.run_play()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("original governor and EPP were restored", result.stdout)
        self.assertEqual(self.snapshot(), before)
