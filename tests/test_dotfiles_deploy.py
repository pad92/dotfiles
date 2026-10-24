"""Exercise individual file deployment, backups and reloads in a temporary home."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from ansible_test_environment import ansible_test_environment

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
class DotfilesDeployTests(unittest.TestCase):
    def test_individual_file_copy_preserves_deployment_behavior(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            role = work / "dotfiles"
            shutil.copytree(ROOT / "ansible/roles/dotfiles", role, symlinks=True)
            handlers = yaml.safe_load((role / "handlers/main.yml").read_text())
            # Observe notifications without touching the desktop or user services.
            (role / "handlers/main.yml").write_text(
                yaml.safe_dump(
                    [
                        {
                            "name": handler["name"],
                            "ansible.builtin.debug": {"msg": handler["name"]},
                        }
                        for handler in handlers
                    ]
                )
            )
            source = role / "files/home"
            (source / ".config/test-systemd/user").mkdir(parents=True)
            mako = source / ".config/mako/config"
            mako.write_text("original\n")
            (mako.parent / ".hidden").write_text("hidden\n")
            (mako.parent / "alias").symlink_to("config")
            (source / ".config/empty-root").mkdir()

            home = work / "home"
            play = [
                {
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "dotfiles_home": str(home),
                        "dotfiles_repository": str(ROOT),
                        "dotfiles_directories": [
                            "./.config/mako/",
                            ".config/waybar",
                            ".config/empty-root",
                        ],
                        "dotfiles_files": [".gitconfig"],
                        "dotfiles_links": [{"src": ".vim", "dest": ".vim"}],
                        "dotfiles_templates": [],
                        "dotfiles_systemd_graphical_units": [],
                        "dotfiles_systemd_directory": ".config/test-systemd",
                        "dotfiles_waybar_host_config": "config.PadsTower",
                    },
                    "tasks": [
                        {
                            "ansible.builtin.import_role": {
                                "name": str(role),
                                "tasks_from": "deploy",
                            },
                            "tags": ["dotfiles_deploy"],
                        }
                    ],
                }
            ]
            playbook = work / "play.yml"
            playbook.write_text(yaml.safe_dump(play))

            def run(*arguments):
                result = subprocess.run(
                    [
                        "ansible-playbook",
                        "-i",
                        "localhost,",
                        str(playbook),
                        "--tags",
                        "dotfiles_deploy",
                        *arguments,
                    ],
                    cwd=ROOT,
                    env=ansible_test_environment(work),
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return result.stdout

            run("--check")
            self.assertFalse(home.exists())
            conflict = home / ".vim"
            conflict.mkdir(parents=True, mode=0o700)
            (conflict / "local").write_text("preserve me")
            inode = conflict.stat().st_ino
            self.assertIn("Replacement tasks are deferred", run("--check"))
            self.assertFalse((home / ".vim.bak").exists())
            output = run()
            self.assertEqual((home / ".vim.bak").stat().st_ino, inode)
            self.assertEqual((home / ".vim.bak/local").read_text(), "preserve me")

            self.assertEqual((home / ".config/mako/.hidden").read_text(), "hidden\n")
            self.assertEqual((home / ".config/mako/alias").read_text(), "original\n")
            self.assertTrue((home / ".config/empty-root").is_dir())
            target = home / ".config/mako/config"
            self.assertTrue(target.exists(), output)
            self.assertEqual(target.read_text(), "original\n")
            self.assertRegex(run(), r"changed=0\b")

            # A local edit with identical size and mtime still needs a backup.
            original_stat = target.stat()
            target.write_text("modified\n")
            os.utime(target, ns=(original_stat.st_atime_ns, mako.stat().st_mtime_ns))
            unmanaged = home / ".config/mako/local-only"
            unmanaged.write_text("keep me\n")
            output = run("--check")
            self.assertEqual(target.read_text(), "modified\n")
            self.assertIn("Copy files individually from .config/mako", output)
            output = run()
            self.assertEqual(target.read_text(), "original\n")
            self.assertTrue(
                any(
                    p.read_text() == "modified\n"
                    for p in target.parent.glob("config.*~")
                )
            )
            self.assertEqual(unmanaged.read_text(), "keep me\n")
            self.assertIn("RUNNING HANDLER [", output)
            self.assertIn("dotfiles : Reload Mako configuration", output)
            self.assertNotIn("dotfiles : Reload Waybar", output)
            self.assertNotRegex(
                output,
                r"changed: \[localhost\].*home/\.config/waybar",
            )

            # File modes and empty directories are part of deployment too.
            target.chmod(0o600)
            target.parent.chmod(0o700)
            (source / ".config/mako/empty").mkdir()
            run()
            self.assertEqual(target.stat().st_mode & 0o777, mako.stat().st_mode & 0o777)
            self.assertTrue((home / ".config/mako/empty").is_dir())
            self.assertEqual(target.parent.stat().st_mode & 0o777, 0o700)
            self.assertRegex(run(), r"changed=0\b")

            # Each source file is checked and reported through its own copy task.
            mako.write_text("updated\n")
            output = run()
            self.assertIn(str(target), output)
            self.assertEqual(target.read_text(), "updated\n")
            self.assertRegex(run(), r"changed=0\b")
