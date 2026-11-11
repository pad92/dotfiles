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
    def test_rendered_dotfiles_notify_only_their_own_handlers(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            role = work / "dotfiles"
            shutil.copytree(ROOT / "ansible/roles/dotfiles", role, symlinks=True)
            # A template with no handler, changed independently of the theme.
            (role / "templates/home/unrelated.j2").write_text(
                "{{ dotfiles_test_value }}\n"
            )
            handlers = yaml.safe_load((role / "handlers/main.yml").read_text())
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
            home = work / "home"
            home.mkdir()
            play = [
                {
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "dotfiles_home": str(home),
                        "dotfiles_directories": [],
                        "dotfiles_files": [],
                        "dotfiles_links": [],
                        "dotfiles_templates": [
                            {"src": "home/.gtkrc-2.0.j2", "dest": ".gtkrc-2.0"},
                            {
                                "src": "home/.config/gtk-3.0/settings.ini.j2",
                                "dest": ".config/gtk-3.0/settings.ini",
                            },
                            {
                                "src": "home/.config/hypr/hyprtoolkit.conf.j2",
                                "dest": ".config/hypr/hyprtoolkit.conf",
                            },
                            {
                                "src": "home/.config/mako/config.j2",
                                "dest": ".config/mako/config",
                            },
                            {"src": "home/unrelated.j2", "dest": ".unrelated"},
                        ],
                        "dotfiles_systemd_graphical_units": [],
                        "dotfiles_waybar_host_config": "config.test",
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

            # User units are covered by test_ansible_regressions; deploying the
            # shipped ones here would triple the cost of every run.
            def deploy(theme, value="first"):
                return run(
                    "--skip-tags",
                    "systemd",
                    "-e",
                    f"dotfiles_icon_theme={theme}",
                    "-e",
                    f"dotfiles_test_value={value}",
                )

            mako_reload = ": Reload Mako configuration]"
            launcher_restart = ": Restart Hyprlauncher]"

            deploy("Example-Dark")
            output = deploy("Other-Dark")
            self.assertIn(mako_reload, output)
            self.assertIn(launcher_restart, output)
            self.assertIn(
                'gtk-icon-theme-name="Other-Dark"',
                (home / ".gtkrc-2.0").read_text(),
            )
            self.assertIn(
                "gtk-icon-theme-name=Other-Dark",
                (home / ".config/gtk-3.0/settings.ini").read_text(),
            )
            self.assertIn(
                "icon_theme = Other-Dark",
                (home / ".config/hypr/hyprtoolkit.conf").read_text(),
            )
            self.assertIn(
                "icon-path=/usr/share/icons/Other-Dark:/usr/share/icons/Other",
                (home / ".config/mako/config").read_text(),
            )
            output = deploy("Other-Dark")
            self.assertRegex(output, r"changed=0\b")
            self.assertNotIn("RUNNING HANDLER", output)

            # Reverting local drift in one file runs only that file's handler.
            toolkit = home / ".config/hypr/hyprtoolkit.conf"
            toolkit.write_text(toolkit.read_text() + "# local edit\n")
            output = deploy("Other-Dark")
            self.assertNotIn("# local edit", toolkit.read_text())
            self.assertIn(launcher_restart, output)
            self.assertNotIn(mako_reload, output)

            # A rendered file without a handler notifies nothing.
            output = deploy("Other-Dark", "second")
            self.assertEqual((home / ".unrelated").read_text(), "second\n")
            self.assertNotIn("RUNNING HANDLER", output)

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
            # Each deployed file costs one Ansible module run per play, so keep
            # only the Waybar files this test relies on: the host-specific
            # configuration and one executable in a subdirectory.
            waybar = source / ".config/waybar"
            kept = {"config.PadsTower", "modules/lact-profile"}
            for path in sorted(waybar.rglob("*"), reverse=True):
                relative = path.relative_to(waybar).as_posix()
                if path.is_dir():
                    if not any(path.iterdir()):
                        path.rmdir()
                elif relative not in kept:
                    path.unlink()
            (source / ".config/test-systemd/user").mkdir(parents=True)
            # A fixture directory with its own handler, independent of the
            # directories the role ships.
            sample = source / ".config/sample-app/config"
            sample.parent.mkdir(parents=True)
            sample.write_text("original\n")
            (sample.parent / ".hidden").write_text("hidden\n")
            (sample.parent / "alias").symlink_to("config")
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
                            "./.config/sample-app/",
                            ".config/waybar",
                            ".config/empty-root",
                        ],
                        "dotfiles_directory_handlers": {
                            ".config/sample-app": ["Reload Mako configuration"],
                            ".config/waybar": ["Reload Waybar"],
                        },
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

            self.assertEqual(
                (home / ".config/sample-app/.hidden").read_text(), "hidden\n"
            )
            self.assertEqual(
                (home / ".config/sample-app/alias").read_text(), "original\n"
            )
            self.assertTrue((home / ".config/empty-root").is_dir())
            self.assertEqual(
                (home / ".config/waybar/config").read_text(),
                (waybar / "config.PadsTower").read_text(),
            )
            self.assertTrue(
                os.access(home / ".config/waybar/modules/lact-profile", os.X_OK)
            )
            target = home / ".config/sample-app/config"
            self.assertTrue(target.exists(), output)
            self.assertEqual(target.read_text(), "original\n")
            self.assertRegex(run(), r"changed=0\b")

            # A local edit with identical size and mtime still needs a backup.
            original_stat = target.stat()
            target.write_text("modified\n")
            os.utime(target, ns=(original_stat.st_atime_ns, sample.stat().st_mtime_ns))
            unmanaged = home / ".config/sample-app/local-only"
            unmanaged.write_text("keep me\n")
            output = run("--check")
            self.assertEqual(target.read_text(), "modified\n")
            self.assertIn("Copy files individually from .config/sample-app", output)
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
            (source / ".config/sample-app/empty").mkdir()
            run()
            self.assertEqual(
                target.stat().st_mode & 0o777, sample.stat().st_mode & 0o777
            )
            self.assertTrue((home / ".config/sample-app/empty").is_dir())
            self.assertEqual(target.parent.stat().st_mode & 0o777, 0o700)
            self.assertRegex(run(), r"changed=0\b")

            # Each source file is checked and reported through its own copy task.
            sample.write_text("updated\n")
            output = run()
            self.assertIn(str(target), output)
            self.assertEqual(target.read_text(), "updated\n")
            self.assertRegex(run(), r"changed=0\b")
