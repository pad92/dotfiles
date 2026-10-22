"""Exercise local deployment, backups and selective reloads in a temporary home."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(
    shutil.which("ansible-playbook") and shutil.which("rsync"),
    "requires ansible-playbook and rsync",
)
class DotfilesDeployTests(unittest.TestCase):
    def test_local_scan_preserves_copy_behavior(self):
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
            home = work / "home"
            play = [
                {
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "dotfiles_home": str(home),
                        "dotfiles_repository": str(ROOT),
                        "dotfiles_directories": ["./.config/mako/", ".config/waybar"],
                        "dotfiles_files": [".gitconfig"],
                        "dotfiles_links": [],
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
                    env={**os.environ, "ANSIBLE_LOCAL_TEMP": str(work / "tmp")},
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return result.stdout

            run()
            target = home / ".config/mako/config"
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
            self.assertIn("Copy static directory .config/mako", output)
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
            self.assertNotIn("Copy static directory .config/waybar", output)

            # File modes and empty directories are part of deployment too.
            target.chmod(0o600)
            (source / ".config/mako/empty").mkdir()
            run()
            self.assertEqual(target.stat().st_mode & 0o777, mako.stat().st_mode & 0o777)
            self.assertTrue((home / ".config/mako/empty").is_dir())
            self.assertRegex(run(), r"changed=0\b")

            # A failed probe cannot suppress regular copies or their notifications.
            binary = work / "bin"
            binary.mkdir()
            rsync = binary / "rsync"
            rsync.write_text("#!/bin/sh\necho 'probe unavailable' >&2\nexit 23\n")
            rsync.chmod(0o755)
            play[0]["environment"] = {"PATH": f"{binary}:{os.environ['PATH']}"}
            playbook.write_text(yaml.safe_dump(play))
            mako.write_text("updated\n")
            output = run()
            self.assertIn("probe unavailable", output)
            self.assertEqual(target.read_text(), "updated\n")
            self.assertRegex(run(), r"changed=0\b")
