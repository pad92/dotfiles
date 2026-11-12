"""Exercise individual file deployment, backups and reloads in a temporary home."""

import getpass
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from ansible_test_environment import ansible_test_environment
from git_fixtures import git, repository

ROOT = Path(__file__).resolve().parents[1]
# The role owns its files by the SSH user that tasks/target.yml describes.
USER_FACTS = {"user_id": getpass.getuser(), "user_gid": os.getgid()}


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
                        "ansible_facts": USER_FACTS,
                        "dotfiles_home": str(home),
                        "dotfiles_directories": [],
                        "dotfiles_files": [],
                        "dotfiles_source_repository": str(ROOT),
                        "dotfiles_trees": [],
                        "dotfiles_plugin_managers": [],
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
            # only the Waybar file this test relies on: one executable in a
            # subdirectory.
            waybar = source / ".config/waybar"
            kept = {"modules/lact-profile"}
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
                        "ansible_facts": USER_FACTS,
                        "dotfiles_home": str(home),
                        "dotfiles_source_repository": str(ROOT),
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
                        "dotfiles_trees": [],
                        "dotfiles_plugin_managers": [],
                        "dotfiles_templates": [],
                        "dotfiles_systemd_graphical_units": [],
                        "dotfiles_systemd_directory": ".config/test-systemd",
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
            # A directory where a file is managed is moved aside whole.
            conflict = home / ".gitconfig"
            conflict.mkdir(parents=True, mode=0o700)
            (conflict / "local").write_text("preserve me")
            inode = conflict.stat().st_ino
            self.assertIn("Replacement tasks are deferred", run("--check"))
            self.assertFalse((home / ".gitconfig.bak").exists())
            output = run()
            self.assertEqual((home / ".gitconfig.bak").stat().st_ino, inode)
            self.assertEqual((home / ".gitconfig.bak/local").read_text(), "preserve me")

            self.assertEqual(
                (home / ".config/sample-app/.hidden").read_text(), "hidden\n"
            )
            self.assertEqual(
                (home / ".config/sample-app/alias").read_text(), "original\n"
            )
            self.assertTrue((home / ".config/empty-root").is_dir())
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


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
class DotfilesTreeCopyTests(unittest.TestCase):
    """The home must keep working once the repository clone is deleted."""

    def test_legacy_link_becomes_a_copy_that_outlives_the_clone(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            role = work / "dotfiles"
            shutil.copytree(ROOT / "ansible/roles/dotfiles", role, symlinks=True)

            # The controller's repository: what Git tracks is deployed, not
            # the Vim backups lying in its own working copy.
            source = work / "source"
            repository(source)
            (source / "home/.vim/config").mkdir(parents=True)
            (source / "home/.vim/config/plugins.vim").write_text("new\n")
            (source / ".gitignore").write_text("backup/\n")
            (source / "wallpaper.png").write_text("png\n")
            git(source, "add", ".")
            git(source, "commit", "-q", "-m", "source")
            (source / "home/.vim/backup").mkdir()
            (source / "home/.vim/backup/controller~").write_text("controller\n")

            # The target's clone, which an earlier version linked ~/.vim to,
            # with what Vim and Vundle wrote there.
            clone = work / "clone"
            repository(clone)
            linked = clone / "files/home/.vim"
            (linked / "config").mkdir(parents=True)
            (linked / "config/plugins.vim").write_text("old\n")
            git(clone, "add", ".")
            git(clone, "commit", "-q", "-m", "clone")
            (linked / "backup").mkdir()
            (linked / "backup/notes.txt~").write_text("edited\n")
            gruvbox = linked / "bundle/gruvbox"
            repository(gruvbox)
            (gruvbox / "colors.vim").write_text("gruvbox\n")
            # An older version's Vundle submodule: its .git file points into
            # the clone, so it must be cloned again rather than copied.
            (linked / "bundle/Vundle.vim").mkdir()
            (linked / "bundle/Vundle.vim/.git").write_text(
                "gitdir: ../../../../.git/modules/vundle\n"
            )

            vundle = work / "vundle"
            repository(vundle)
            (vundle / "autoload.vim").write_text("vundle\n")
            git(vundle, "add", ".")
            git(vundle, "commit", "-q", "-m", "vundle")

            home = work / "home"
            home.mkdir()
            (home / ".vim").symlink_to(linked)
            play = [
                {
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "ansible_facts": USER_FACTS,
                        "dotfiles_home": str(home),
                        "dotfiles_source_repository": str(source),
                        "dotfiles_source_root": str(source / "home"),
                        "dotfiles_legacy_link_root": str(clone / "files/home"),
                        "dotfiles_trees": [{"src": ".vim", "dest": ".vim"}],
                        "dotfiles_plugin_managers": [
                            {
                                "repo": f"file://{vundle}",
                                "dest": ".vim/bundle/Vundle.vim",
                            }
                        ],
                        "dotfiles_hyprlock_wallpaper_source": "wallpaper.png",
                        "dotfiles_hyprlock_wallpaper": ".local/share/wallpaper.png",
                        "dotfiles_directories": [],
                        "dotfiles_files": [],
                        "dotfiles_templates": [],
                        "dotfiles_systemd_graphical_units": [],
                        "dotfiles_systemd_directory": ".config/test-systemd",
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
            (role / "files/home/.config/test-systemd/user").mkdir(parents=True)
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
                        "--skip-tags",
                        "systemd",
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

            output = run("--check")
            self.assertIn("Check mode stops before replacing the links", output)
            self.assertIn("backup/notes.txt~", output)
            self.assertTrue((home / ".vim").is_symlink())
            self.assertEqual((linked / "config/plugins.vim").read_text(), "old\n")

            output = run()
            self.assertRegex(
                output, r"changed: \[localhost\] => \(item=\.vim/backup/notes"
            )
            vim = home / ".vim"
            self.assertFalse(vim.is_symlink())
            self.assertFalse((home / ".vim.bak").exists())
            self.assertEqual((vim / "config/plugins.vim").read_text(), "new\n")
            self.assertFalse((vim / "backup/controller~").exists())
            self.assertEqual((vim / "backup/notes.txt~").read_text(), "edited\n")
            self.assertEqual(
                (vim / "bundle/gruvbox/colors.vim").read_text(), "gruvbox\n"
            )
            self.assertTrue((vim / "bundle/gruvbox/.git").is_dir())
            self.assertEqual(
                git(vim / "bundle/Vundle.vim", "rev-parse", "HEAD"),
                git(vundle, "rev-parse", "HEAD"),
            )
            self.assertEqual((home / ".local/share/wallpaper.png").read_text(), "png\n")
            # The clone is left as it was.
            self.assertEqual((linked / "config/plugins.vim").read_text(), "old\n")
            self.assertTrue((linked / "backup/notes.txt~").exists())

            shutil.rmtree(clone)
            for path in home.rglob("*"):
                if path.is_symlink():
                    self.assertFalse(os.readlink(path).startswith(str(clone)), path)
            self.assertEqual((vim / "backup/notes.txt~").read_text(), "edited\n")
            self.assertRegex(run(), r"changed=0\b")
