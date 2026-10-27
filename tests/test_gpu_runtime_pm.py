"""Exercise runtime PM rule lifecycle in a temporary directory."""

import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from ansible_test_environment import ansible_test_environment

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "ansible/roles/system"


class RuntimePmTests(unittest.TestCase):
    def test_detection_controls_rule_lifecycle(self):
        for detection in ("unknown", "false", "true"):
            with (
                self.subTest(detection=detection),
                tempfile.TemporaryDirectory() as tmp,
            ):
                work = Path(tmp)
                target = work / "runtime-pm.rules"
                target.write_text("existing rule\n")
                tasks = yaml.safe_load((ROLE / "tasks/gpu_runtime_pm.yml").read_text())
                # Inject the hardware result; exercise the actual Ansible decisions.
                tasks = tasks[1:]
                for task in tasks:
                    if "ansible.builtin.copy" in task:
                        options = task["ansible.builtin.copy"]
                        options["src"] = str(ROLE / "files" / options["src"])
                        options["dest"] = str(target)
                        options.pop("owner")
                        options.pop("group")
                    if "ansible.builtin.file" in task:
                        task["ansible.builtin.file"]["path"] = str(target)
                play = work / "play.yml"
                play.write_text(
                    yaml.safe_dump(
                        [
                            {
                                "hosts": "localhost",
                                "connection": "local",
                                "gather_facts": False,
                                "vars": {
                                    "packages_selected_groups": ["09_nvidia_modern"],
                                    "system_hybrid_laptop_detection": {
                                        "stdout": detection
                                    },
                                },
                                "tasks": tasks,
                            }
                        ]
                    )
                )
                result = subprocess.run(
                    ["ansible-playbook", "-i", "localhost,", str(play)],
                    env=ansible_test_environment(work),
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                if detection == "unknown":
                    self.assertEqual(target.read_text(), "existing rule\n")
                elif detection == "false":
                    self.assertFalse(target.exists())
                else:
                    self.assertEqual(
                        target.read_text(),
                        (
                            ROLE / "files/80-dotfiles-nvidia-runtime-pm.rules"
                        ).read_text(),
                    )
