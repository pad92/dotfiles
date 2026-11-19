"""Exercise runtime PM rule lifecycle in a temporary directory."""

import tempfile
import unittest
from pathlib import Path

import yaml
from ansible_test_environment import ROOT, ansible_test_environment, run_playbook

ROLE = ROOT / "ansible/roles/gpu"


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
                tasks = yaml.safe_load((ROLE / "tasks/runtime_pm.yml").read_text())
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
                                    "gpu_hybrid_laptop_detection": {
                                        "stdout": detection
                                    },
                                },
                                "tasks": tasks,
                                # Never touch the host's udev from this fixture.
                                "handlers": [
                                    {
                                        "name": handler["name"],
                                        "ansible.builtin.debug": {
                                            "msg": handler["name"]
                                        },
                                    }
                                    for handler in yaml.safe_load(
                                        (ROLE / "handlers/main.yml").read_text()
                                    )
                                ],
                            }
                        ]
                    )
                )
                result = run_playbook(
                    play,
                    env=ansible_test_environment(work),
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
