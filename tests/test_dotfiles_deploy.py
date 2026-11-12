"""Exercise individual file deployment, backups and reloads in a temporary home."""

import getpass
import hashlib
import json
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


class DotfilesTreeDefaultsTests(unittest.TestCase):
    """A clone has only what Git tracks, so each copied tree must have some."""

    def test_each_copied_tree_has_tracked_files_on_a_fresh_clone(self):
        defaults = yaml.safe_load(
            (ROOT / "ansible/roles/dotfiles/defaults/main.yml").read_text()
        )
        home = Path("ansible/roles/dotfiles/files/home")
        for tree in defaults["dotfiles_trees"]:
            with self.subTest(tree=tree["src"]):
                tracked = git(ROOT, "ls-files", "--", str(home / tree["src"]))
                if tree.get("copy", True):
                    # dotfiles_tree raises NotADirectoryError on a fresh clone.
                    self.assertTrue(tracked, f"nothing tracked under {tree['src']}")
                else:
                    # Only a destination: tracked files would never be copied.
                    self.assertFalse(tracked, tracked)


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


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
class DotfilesTreeUpdateTests(unittest.TestCase):
    """Later deployments follow the repository: pinned clones and removed files."""

    def test_submodules_are_cloned_and_removed_files_deleted(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            role = work / "dotfiles"
            shutil.copytree(ROOT / "ansible/roles/dotfiles", role, symlinks=True)
            (role / "files/home/.config/test-systemd/user").mkdir(parents=True)

            plugin = work / "plugin"
            repository(plugin)
            (plugin / "plugin.zsh").write_text("v1\n")
            (plugin / "dropped.zsh").write_text("dropped\n")
            git(plugin, "add", ".")
            git(plugin, "commit", "-q", "-m", "v1")
            first = git(plugin, "rev-parse", "HEAD")

            source = work / "source"
            repository(source)
            zsh = source / "home/zsh"
            (zsh / "completions").mkdir(parents=True)
            (zsh / "completions/_kept").write_text("kept\n")
            (zsh / "completions/_removed").write_text("removed\n")
            (zsh / "completions/_edited").write_text("shipped\n")
            (source / "wallpaper.png").write_text("png\n")
            git(source, "add", ".")
            git(source, "commit", "-q", "-m", "source")
            git(
                source,
                "-c",
                "protocol.file.allow=always",
                "submodule",
                "add",
                "-q",
                f"file://{plugin}",
                "home/zsh/plugins/plugin",
            )
            git(source, "commit", "-q", "-m", "plugin")
            # Upstream moves on; the repository still records the first commit.
            (plugin / "unrecorded.zsh").write_text("unrecorded\n")
            git(plugin, "add", ".")
            git(plugin, "commit", "-q", "-m", "unrecorded")
            # The controller does not need the submodule checked out.
            git(
                source,
                "submodule",
                "deinit",
                "-q",
                "--force",
                "home/zsh/plugins/plugin",
            )

            home = work / "home"
            target = home / ".local/share/dotfiles/zsh"
            # An earlier version copied the plugin, without its .git.
            (target / "plugins/plugin").mkdir(parents=True)
            (target / "plugins/plugin/plugin.zsh").write_text("copied\n")
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
                        "dotfiles_legacy_link_root": str(work / "no-clone"),
                        "dotfiles_trees": [
                            {"src": ".tmux", "dest": ".tmux", "copy": False},
                            {"src": "zsh", "dest": ".local/share/dotfiles/zsh"},
                        ],
                        "dotfiles_plugin_managers": [],
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

            manifest = (
                home
                / ".local/state/dotfiles/manifests/.local%2Fshare%2Fdotfiles%2Fzsh.json"
            )
            clone = target / "plugins/plugin"

            # Check mode plans the backup and changes nothing.
            output = run("--check")
            self.assertIn(f"{clone} -> {clone}.bak", output)
            self.assertFalse((target / "plugins/plugin.bak").exists())
            self.assertFalse((clone / ".git").exists())
            self.assertFalse(manifest.exists())

            run()
            self.assertTrue((home / ".tmux").is_dir())
            # The copy is kept as a backup, and the clone is at the recorded
            # commit, with its own metadata.
            self.assertEqual(
                (target / "plugins/plugin.bak/plugin.zsh").read_text(), "copied\n"
            )
            self.assertEqual(git(clone, "rev-parse", "HEAD"), first)
            self.assertEqual((clone / "plugin.zsh").read_text(), "v1\n")
            self.assertFalse((clone / "unrecorded.zsh").exists())
            recorded = json.loads(manifest.read_text())["files"]
            self.assertEqual(
                sorted(recorded),
                [
                    str(target / "completions/_edited"),
                    str(target / "completions/_kept"),
                    str(target / "completions/_removed"),
                ],
            )
            self.assertRegex(run(), r"changed=0\b")

            # Upstream drops a file and the repository records the new commit.
            git(plugin, "rm", "-q", "dropped.zsh", "unrecorded.zsh")
            (plugin / "plugin.zsh").write_text("v2\n")
            git(plugin, "commit", "-q", "-am", "v2")
            second = git(plugin, "rev-parse", "HEAD")
            git(
                source,
                "update-index",
                "--cacheinfo",
                f"160000,{second},home/zsh/plugins/plugin",
            )
            # The repository drops two completions, one of them edited on the
            # target, and the user adds one of their own.
            git(
                source,
                "rm",
                "-q",
                "home/zsh/completions/_removed",
                "home/zsh/completions/_edited",
            )
            git(source, "commit", "-q", "-m", "update")
            (target / "completions/_edited").write_text("edited\n")
            (target / "completions/_local").write_text("local\n")

            output = run("--check")
            self.assertTrue((target / "completions/_removed").exists())
            self.assertEqual(git(clone, "rev-parse", "HEAD"), first)

            output = run()
            self.assertEqual(git(clone, "rev-parse", "HEAD"), second)
            self.assertFalse((clone / "dropped.zsh").exists())
            self.assertFalse((target / "completions/_removed").exists())
            self.assertEqual((target / "completions/_edited").read_text(), "edited\n")
            self.assertIn("_edited was changed by hand, so it is kept", output)
            self.assertEqual((target / "completions/_local").read_text(), "local\n")
            self.assertEqual((target / "completions/_kept").read_text(), "kept\n")
            self.assertEqual(
                sorted(json.loads(manifest.read_text())["files"]),
                [str(target / "completions/_kept")],
            )
            self.assertRegex(run(), r"changed=0\b")

            # A hand-edited manifest that names a file outside the tree, with
            # its current checksum, must not delete it.
            outside = target.parent / "outside"
            outside.write_text("outside\n")
            edited = json.loads(manifest.read_text())
            edited["files"][f"{target}/../outside"] = hashlib.sha1(
                outside.read_bytes(), usedforsecurity=False
            ).hexdigest()
            manifest.write_text(json.dumps(edited))
            run()
            self.assertEqual(outside.read_text(), "outside\n")
