"""Exercise check mode and changed-path output without deploying to the host."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from ansible_test_environment import ansible_test_environment

ROOT = Path(__file__).resolve().parents[1]


class FileContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def run_play(self, play, *arguments, environment=None):
        path = self.work / "play.yml"
        path.write_text(yaml.safe_dump(play))
        result = subprocess.run(
            ["ansible-playbook", "-i", "localhost,", str(path), *arguments],
            cwd=ROOT,
            env={
                **ansible_test_environment(self.work),
                **(environment or {}),
            },
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_initramfs_handler_reports_generated_file(self):
        bindir = self.work / "bin"
        bindir.mkdir()
        output_dir = self.work / "images"
        output_dir.mkdir()
        generator = bindir / "dracut"
        generator.write_text('#!/bin/sh\nprintf image > "$TEST_IMAGE"\n')
        generator.chmod(0o755)
        image = output_dir / "image"
        handlers = yaml.safe_load(
            (ROOT / "ansible/roles/gpu/handlers/main.yml").read_text()
        )
        output = self.run_play(
            [
                {
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "gpu_initramfs_generator_effective": "dracut",
                        "gpu_initramfs_report_roots": [str(output_dir)],
                    },
                    "handlers": handlers,
                    "tasks": [
                        {
                            "ansible.builtin.debug": {
                                "msg": "Trigger isolated handler"
                            },
                            "changed_when": True,
                            "notify": "Regenerate Arch initramfs",
                        }
                    ],
                }
            ],
            environment={
                "PATH": f"{bindir}:{os.environ['PATH']}",
                "TEST_IMAGE": str(image),
            },
        )
        self.assertIn("RUNNING HANDLER [Report regenerated initramfs files]", output)
        self.assertIn(str(image), output)
        self.assertEqual(image.read_text(), "image")

    def test_sysctl_plan_uses_template_without_existing_target(self):
        # Only parse the intended configuration: never invoke sysctl in this fixture.
        task = next(
            task
            for task in yaml.safe_load(
                (
                    ROOT / "ansible/roles/hardening/tasks/kernel_hardening.yml"
                ).read_text()
            )
            if task["name"] == "Parse the intended desktop sysctl settings"
        )
        template = ROOT / "ansible/roles/hardening/templates/hardening.conf.j2"
        expression = task["ansible.builtin.set_fact"]["hardening_policy_entries"]
        task["ansible.builtin.set_fact"]["hardening_policy_entries"] = (
            expression.replace("'hardening.conf.j2'", repr(str(template)))
        )
        self.run_play(
            [
                {
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "ansible_facts": {"hostname": "fixture"},
                        "hardening_ipv6_enabled": True,
                        "hardening_optional_sysctls": {
                            "results": [{"stat": {"exists": False}}] * 4
                        },
                    },
                    "tasks": [
                        task,
                        {
                            "ansible.builtin.assert": {
                                "that": "hardening_policy_entries | length > 0"
                            }
                        },
                    ],
                }
            ],
            "--check",
        )

    def test_superseded_sysctl_files_are_backed_up_before_removal(self):
        sysctl_dir = self.work / "sysctl.d"
        sysctl_dir.mkdir()
        old_files = [
            "hardening.conf",
            "zz-dotfiles-hardening.conf",
            "zz-dotfiles-bpf.conf",
        ]
        for name in old_files:
            (sysctl_dir / name).write_text(f"old {name}\n")

        tasks = yaml.safe_load(
            (ROOT / "ansible/roles/hardening/tasks/kernel_hardening.yml").read_text()
        )
        migration_start = next(
            index
            for index, task in enumerate(tasks)
            if task["name"] == "Check for superseded dotfiles sysctl files"
        )
        migration_tasks = yaml.safe_load(
            yaml.safe_dump(tasks[migration_start:]).replace(
                "/etc/sysctl.d", str(sysctl_dir)
            )
        )
        for task in migration_tasks:
            if "ansible.builtin.copy" in task:
                task["ansible.builtin.copy"].pop("owner", None)
                task["ansible.builtin.copy"].pop("group", None)

        output = self.run_play(
            [
                {
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "hardening_optional_sysctls": {
                            "results": [
                                {"stat": {"exists": True}},
                                {"stat": {"exists": True}},
                                {"stat": {"exists": True}},
                                {"stat": {"exists": True}},
                            ]
                        }
                    },
                    "tasks": migration_tasks,
                }
            ]
        )
        for name in old_files:
            self.assertFalse((sysctl_dir / name).exists(), output)
            self.assertEqual(
                (sysctl_dir / f"{name}.dotfiles-backup").read_text(), f"old {name}\n"
            )
