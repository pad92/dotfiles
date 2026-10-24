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

    def test_backup_check_mode_collects_and_preserves_files(self):
        home = self.work / "home"
        home.mkdir()
        backup = home / ".zshrc.bak"
        backup.write_text("keep")
        play = yaml.safe_load((ROOT / "ansible/backup.yml").read_text())
        play[0]["tasks"][0]["ansible.builtin.command"]["argv"][1] = str(
            ROOT / "scripts/ansible_backup_files.py"
        )
        output = self.run_play(
            play,
            "--check",
            "-e",
            "dotfiles_backup_action=remove",
            environment={
                "ANSIBLE_BACKUP_ROOT": str(home),
                # This check only exercises role defaults, not encrypted host vars.
                "ANSIBLE_VARS_ENABLED": "",
            },
        )
        self.assertIn(str(backup), output)
        self.assertEqual(backup.read_text(), "keep")

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
            (ROOT / "ansible/roles/system/handlers/main.yml").read_text()
        )
        output = self.run_play(
            [
                {
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "system_initramfs_generator_effective": "dracut",
                        "system_initramfs_report_roots": [str(output_dir)],
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

    def test_first_vim_clone_reports_paths_and_second_run_is_unchanged(self):
        repo = self.work / "plugin"
        repo.mkdir()

        def git(*args):
            subprocess.run(
                ["git", "-C", str(repo), *args], check=True, capture_output=True
            )

        git("init")
        git("config", "user.name", "Test")
        git("config", "user.email", "test@example.invalid")
        git("config", "commit.gpgsign", "false")
        (repo / "plugin.vim").write_text('" test\n')
        git("add", ".")
        git("commit", "-m", "fixture")
        home = self.work / "home"
        play = [
            {
                "hosts": "localhost",
                "connection": "local",
                "gather_facts": False,
                "vars": {
                    "dotfiles_home": str(home),
                    "dotfiles_update_vim_plugins": True,
                    "dotfiles_vim_plugins": [{"repo": str(repo), "dest": "plugin"}],
                },
                "tasks": [
                    {
                        "ansible.builtin.import_tasks": str(
                            ROOT / "ansible/roles/dotfiles/tasks/runtime.yml"
                        )
                    }
                ],
            }
        ]
        output = self.run_play(play)
        self.assertIn(str(home / ".vim/bundle/plugin/plugin.vim"), output)
        self.assertRegex(self.run_play(play), r"changed=0\b")
        play[0]["vars"]["dotfiles_update_vim_plugins"] = False
        self.assertRegex(self.run_play(play), r"changed=0\b")

    def test_sysctl_plan_uses_template_without_existing_target(self):
        # Only parse the intended configuration: never invoke sysctl in this fixture.
        task = next(
            task
            for task in yaml.safe_load(
                (ROOT / "ansible/roles/system/tasks/kernel_hardening.yml").read_text()
            )
            if task["name"] == "Parse the intended desktop sysctl settings"
        )
        template = ROOT / "ansible/roles/system/templates/hardening.conf.j2"
        expression = task["ansible.builtin.set_fact"]["system_hardening_policy_entries"]
        task["ansible.builtin.set_fact"]["system_hardening_policy_entries"] = (
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
                        "system_ipv6_enabled_default": True,
                        "system_optional_sysctls": {
                            "results": [{"stat": {"exists": False}}] * 4
                        },
                        "packages_host_groups": {},
                        "system_ipv6_enabled_by_hostname": {},
                    },
                    "tasks": [
                        task,
                        {
                            "ansible.builtin.assert": {
                                "that": "system_hardening_policy_entries | length > 0"
                            }
                        },
                    ],
                }
            ],
            "--check",
        )
