"""Exercise individual file deployment, backups and reloads in a temporary home."""

import getpass
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from ansible_test_environment import ansible_test_environment
from git_fixtures import git, repository
from vim_fixtures import VIM_ERROR, start_vim

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
                        "dotfiles_vim_pack_plugins": [],
                        "dotfiles_zsh_plugins": [],
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
                        "dotfiles_vim_pack_plugins": [],
                        "dotfiles_zsh_plugins": [],
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
                # dotfiles_tree raises NotADirectoryError on a fresh clone.
                self.assertTrue(tracked, f"nothing tracked under {tree['src']}")

    def test_zsh_plugins_are_pinned_and_loaded(self):
        defaults = yaml.safe_load(
            (ROOT / "ansible/roles/dotfiles/defaults/main.yml").read_text()
        )
        zshrc = (ROOT / "ansible/roles/dotfiles/templates/home/.zshrc.j2").read_text()
        block = re.search(r"^plugins=\((.*?)\)", zshrc, re.M | re.S).group(1)
        loaded = [
            word for line in block.splitlines() for word in line.split("#")[0].split()
        ]
        plugins = Path("ansible/roles/dotfiles/files/home/zsh/plugins")
        self.assertTrue(defaults["dotfiles_zsh_plugins"])
        for plugin in defaults["dotfiles_zsh_plugins"]:
            name = Path(plugin["dest"]).name
            with self.subTest(plugin=name):
                # A branch or tag would move without a change to the repository.
                self.assertRegex(plugin["version"], r"^[0-9a-f]{40}$")
                self.assertEqual(
                    plugin["dest"], f"{{{{ dotfiles_zsh_dest }}}}/plugins/{name}"
                )
                self.assertIn(name, loaded)
                # The copy would land in the clone's working tree.
                self.assertFalse(git(ROOT, "ls-files", "--", str(plugins / name)))

        # init.zsh skips a plugin it cannot find, so a missing one goes unseen.
        shipped = {
            Path(path).relative_to(plugins).parts[0]
            for path in git(ROOT, "ls-files", "--", str(plugins)).splitlines()
        }
        cloned = {
            Path(plugin["dest"]).name for plugin in defaults["dotfiles_zsh_plugins"]
        }
        self.assertEqual(sorted(set(loaded) - shipped - cloned), [])


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
            (source / "home/zsh").mkdir()
            (source / "home/zsh/init.zsh").write_text("new\n")
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
            linked_zsh = clone / "files/home/zsh"
            linked_zsh.mkdir()
            (linked_zsh / "init.zsh").write_text("old\n")
            git(clone, "add", ".")
            git(clone, "commit", "-q", "-m", "clone")
            # A Zsh plugin that an older version shipped as a submodule, left
            # behind once the clone dropped its gitlink: the .git file points
            # into the clone, and the files are those of an older commit.
            stale = linked_zsh / "plugins/zsh-plugin"
            stale.mkdir(parents=True)
            (stale / ".git").write_text("gitdir: ../../../../../.git/modules/zsh\n")
            (stale / "plugin.zsh").write_text("stale\n")
            (linked / "backup").mkdir()
            (linked / "backup/notes.txt~").write_text("edited\n")
            gruvbox = linked / "bundle/gruvbox"
            repository(gruvbox)
            (gruvbox / "colors.vim").write_text("gruvbox\n")

            vim_plugin = work / "vim-plugin"
            repository(vim_plugin)
            (vim_plugin / "plugin.vim").write_text("pinned\n")
            git(vim_plugin, "add", ".")
            git(vim_plugin, "commit", "-q", "-m", "pinned")
            vim_pinned = git(vim_plugin, "rev-parse", "HEAD")
            (vim_plugin / "plugin.vim").write_text("later\n")
            git(vim_plugin, "commit", "-q", "-am", "later")

            zsh_plugin = work / "zsh-plugin"
            repository(zsh_plugin)
            (zsh_plugin / "plugin.zsh").write_text("pinned\n")
            git(zsh_plugin, "add", ".")
            git(zsh_plugin, "commit", "-q", "-m", "pinned")
            pinned = git(zsh_plugin, "rev-parse", "HEAD")
            (zsh_plugin / "plugin.zsh").write_text("later\n")
            git(zsh_plugin, "commit", "-q", "-am", "later")

            home = work / "home"
            home.mkdir()
            (home / ".vim").symlink_to(linked)
            (home / ".local/share/dotfiles").mkdir(parents=True)
            (home / ".local/share/dotfiles/zsh").symlink_to(linked_zsh)
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
                        "dotfiles_trees": [
                            {"src": ".vim", "dest": ".vim"},
                            {"src": "zsh", "dest": ".local/share/dotfiles/zsh"},
                        ],
                        "dotfiles_vim_pack_plugins": [
                            {
                                "repo": f"file://{vim_plugin}",
                                "dest": ".vim/pack/dotfiles/start/vim-plugin",
                                "version": vim_pinned,
                            }
                        ],
                        "dotfiles_zsh_plugins": [
                            {
                                "repo": f"file://{zsh_plugin}",
                                "dest": ".local/share/dotfiles/zsh/plugins/zsh-plugin",
                                "version": pinned,
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
            # A plugin Vundle had installed is copied, and left unused.
            self.assertTrue((vim / "bundle/gruvbox/.git").is_dir())
            pack = vim / "pack/dotfiles/start/vim-plugin"
            self.assertEqual(git(pack, "rev-parse", "HEAD"), vim_pinned)
            self.assertEqual((pack / "plugin.vim").read_text(), "pinned\n")
            # The Zsh plugin is cloned at its pinned commit, not copied from
            # the clone with its broken .git file.
            zsh = home / ".local/share/dotfiles/zsh"
            self.assertFalse(zsh.is_symlink())
            self.assertEqual((zsh / "init.zsh").read_text(), "new\n")
            self.assertTrue((zsh / "plugins/zsh-plugin/.git").is_dir())
            self.assertEqual(
                git(zsh / "plugins/zsh-plugin", "rev-parse", "HEAD"), pinned
            )
            self.assertEqual(
                (zsh / "plugins/zsh-plugin/plugin.zsh").read_text(), "pinned\n"
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

    def test_zsh_plugins_follow_their_pin_and_removed_files_are_deleted(self):
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
            # Upstream moves on; the role still pins the first commit.
            (plugin / "unpinned.zsh").write_text("unpinned\n")
            git(plugin, "add", ".")
            git(plugin, "commit", "-q", "-m", "unpinned")

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

            home = work / "home"
            target = home / ".local/share/dotfiles/zsh"
            playbook = work / "play.yml"

            def write_play(version):
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
                                {"src": "zsh", "dest": ".local/share/dotfiles/zsh"},
                            ],
                            "dotfiles_vim_pack_plugins": [],
                            "dotfiles_zsh_plugins": [
                                {
                                    "repo": f"file://{plugin}",
                                    "dest": ".local/share/dotfiles/zsh/plugins/plugin",
                                    "version": version,
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

            write_play(first)
            run()
            # The clone is at the pinned commit, with its own metadata.
            self.assertEqual(git(clone, "rev-parse", "HEAD"), first)
            self.assertEqual((clone / "plugin.zsh").read_text(), "v1\n")
            self.assertFalse((clone / "unpinned.zsh").exists())
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

            # Upstream drops a file and the role pins the new commit.
            git(plugin, "rm", "-q", "dropped.zsh", "unpinned.zsh")
            (plugin / "plugin.zsh").write_text("v2\n")
            git(plugin, "commit", "-q", "-am", "v2")
            second = git(plugin, "rev-parse", "HEAD")
            write_play(second)
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

            run("--check")
            self.assertTrue((target / "completions/_removed").exists())
            self.assertEqual(git(clone, "rev-parse", "HEAD"), first)

            output = run()
            self.assertEqual(git(clone, "rev-parse", "HEAD"), second)
            self.assertEqual((clone / "plugin.zsh").read_text(), "v2\n")
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


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
@unittest.skipUnless(shutil.which("vim"), "vim is not installed")
class DotfilesVimPackTests(unittest.TestCase):
    """Vim plugins are pinned clones in a Vim package, without Vundle or tpm."""

    def test_upgrade_from_vundle_and_tpm_clones_keeps_them_and_loads_the_pack(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            role = work / "dotfiles"
            shutil.copytree(ROOT / "ansible/roles/dotfiles", role, symlinks=True)
            (role / "files/home/.config/test-systemd/user").mkdir(parents=True)

            plugin = work / "plugin"
            repository(plugin)
            (plugin / "colors").mkdir()
            (plugin / "colors/gruvbox.vim").write_text(
                "let g:colors_name = 'gruvbox'\n"
            )
            (plugin / "plugin").mkdir()
            (plugin / "plugin/fixture.vim").write_text("let g:fixture = 'v1'\n")
            (plugin / "plugin/dropped.vim").write_text("let g:dropped = 1\n")
            git(plugin, "add", ".")
            git(plugin, "commit", "-q", "-m", "v1")
            first = git(plugin, "rev-parse", "HEAD")
            git(plugin, "rm", "-q", "plugin/dropped.vim")
            (plugin / "plugin/fixture.vim").write_text("let g:fixture = 'v2'\n")
            git(plugin, "commit", "-q", "-am", "v2")
            second = git(plugin, "rev-parse", "HEAD")

            # A home deployed by the previous version: Vundle and tpm cloned
            # by the role, a plugin Vundle installed, and the same tmux
            # directory the role created.
            home = work / "home"
            managers = {}
            for path, script in (
                (".vim/bundle/Vundle.vim", "autoload/vundle.vim"),
                (".tmux/plugins/tpm", "tpm"),
            ):
                repository(home / path)
                (home / path / script).parent.mkdir(parents=True, exist_ok=True)
                (home / path / script).write_text("echoerr 'loaded'\n")
                git(home / path, "add", ".")
                git(home / path, "commit", "-q", "-m", "manager")
                managers[path] = git(home / path, "rev-parse", "HEAD")
            (home / ".vim/bundle/gruvbox/colors").mkdir(parents=True)
            (home / ".vim/bundle/gruvbox/colors/gruvbox.vim").write_text(
                "echoerr 'the Vundle gruvbox was loaded'\n"
            )

            dest = ".vim/pack/dotfiles/start/fixture"
            playbook = work / "play.yml"

            def write_play(version):
                play = [
                    {
                        "hosts": "localhost",
                        "connection": "local",
                        "gather_facts": False,
                        "vars": {
                            "ansible_facts": USER_FACTS,
                            "dotfiles_home": str(home),
                            # The real .vim tree and .vimrc, as Git tracks them.
                            "dotfiles_source_repository": str(ROOT),
                            "dotfiles_source_root": str(
                                ROOT / "ansible/roles/dotfiles/files/home"
                            ),
                            "dotfiles_legacy_link_root": str(work / "no-clone"),
                            "dotfiles_trees": [{"src": ".vim", "dest": ".vim"}],
                            "dotfiles_zsh_plugins": [],
                            "dotfiles_vim_pack_plugins": [
                                {
                                    "repo": f"file://{plugin}",
                                    "dest": dest,
                                    "version": version,
                                }
                            ],
                            "dotfiles_directories": [],
                            "dotfiles_files": [".vimrc", ".tmux.conf"],
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
                    timeout=180,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return result.stdout

            def vim(*commands):
                messages = start_vim(home, "scriptnames", *commands)
                self.assertIsNone(VIM_ERROR.search(messages), messages)
                self.assertNotRegex(messages.lower(), r"vundle|/bundle/")
                return messages

            write_play(first)
            run()
            pack = home / dest
            self.assertEqual(git(pack, "rev-parse", "HEAD"), first)
            # The old clones stay where they were, untouched.
            for path, head in managers.items():
                self.assertEqual(git(home / path, "rev-parse", "HEAD"), head)
                self.assertEqual(git(home / path, "status", "--porcelain"), "")
            self.assertTrue((home / ".vim/bundle/gruvbox/colors/gruvbox.vim").exists())
            self.assertNotRegex((home / ".tmux.conf").read_text(), r"tpm|@plugin")
            self.assertRegex(run(), r"changed=0\b")

            messages = vim(
                "echo 'colors=' . g:colors_name", "echo 'fixture=' . g:fixture"
            )
            self.assertIn(f"{dest}/plugin/fixture.vim", messages)
            self.assertIn("colors=gruvbox", messages)
            self.assertIn("fixture=v1", messages)
            self.assertIn(f"{dest}/plugin/dropped.vim", messages)

            # A new pin moves the clone, and the file upstream dropped goes.
            write_play(second)
            run("--check")
            self.assertEqual(git(pack, "rev-parse", "HEAD"), first)
            run()
            self.assertEqual(git(pack, "rev-parse", "HEAD"), second)
            self.assertFalse((pack / "plugin/dropped.vim").exists())
            messages = vim("echo 'fixture=' . g:fixture")
            self.assertIn("fixture=v2", messages)
            self.assertNotIn("dropped.vim", messages)
            self.assertRegex(run(), r"changed=0\b")
