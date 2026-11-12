"""Exercise production modules against temporary files and mocked system boundaries."""

import hashlib
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from git_fixtures import git, repository

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


files = load(
    "ansible.module_utils.dotfiles_files", "ansible/module_utils/dotfiles_files.py"
)
sys.modules["ansible.module_utils.dotfiles_files"] = files
backup = load("backup_module", "ansible/library/dotfiles_backup.py")
sysfs = load("sysfs_module", "ansible/library/dotfiles_sysfs.py")
initramfs = load("initramfs_module", "ansible/library/dotfiles_initramfs.py")
makepkg = load("makepkg_module", "ansible/library/dotfiles_makepkg.py")

tree = load("tree_module", "ansible/library/dotfiles_tree.py")

aur = load("aur_module", "ansible/library/dotfiles_aur.py")

retired = load("retired_module", "ansible/library/dotfiles_retired_plugins.py")


class Result(Exception):
    def __init__(self, failed=False, **data):
        self.failed = failed
        self.data = data


class Module:
    def __init__(self, params, check=False):
        self.params = params
        self.check_mode = check

    def exit_json(self, **data):
        raise Result(**data)

    def fail_json(self, **data):
        raise Result(failed=True, **data)


class ModuleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def invoke(self, implementation, params, check=False):
        with (
            patch.object(
                implementation, "AnsibleModule", return_value=Module(params, check)
            ),
            self.assertRaises(Result) as caught,
        ):
            implementation.main()
        return caught.exception

    def test_aur_installs_only_missing_without_print_format(self):
        with patch.object(
            Module,
            "run_command",
            create=True,
            side_effect=[
                (0, "existing 1\n", ""),
                (127, "new\n", ""),
                (0, "", ""),
                (0, "existing 1\nnew 2\n", ""),
                (0, "", ""),
            ],
        ) as run:
            result = self.invoke(
                aur, {"name": ["existing", "new"], "executable": "yay"}
            )
        self.assertFalse(result.failed)
        self.assertEqual(result.data["changed_packages"], ["new"])
        self.assertEqual(
            run.call_args_list[1].args[0],
            ["pacman", "-T", "--", "existing", "new"],
        )
        self.assertEqual(
            run.call_args_list[2].args[0],
            ["yay", "-S", "--needed", "--noconfirm", "--", "new"],
        )
        self.assertEqual(run.call_args_list[4].args[0], ["pacman", "-T", "--", "new"])

    def test_aur_gives_the_helper_sudo_the_become_password(self):
        # Under Ansible the helper has no terminal, so its sudo must use askpass.
        seen = {}

        def run_command(command, **kwargs):
            if command[0] != "yay":
                return responses.pop(0)
            askpass = kwargs["environ_update"]["SUDO_ASKPASS"]
            seen["command"] = command
            seen["askpass"] = askpass
            seen["mode"] = os.stat(askpass).st_mode & 0o777
            seen["output"] = subprocess.run(
                [askpass, "[sudo] password:"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            return (0, "", "")

        responses = [
            (0, "", ""),
            (127, "new\n", ""),
            (0, "new 1\n", ""),
            (0, "", ""),
        ]
        with patch.object(Module, "run_command", create=True, side_effect=run_command):
            result = self.invoke(
                aur,
                {"name": ["new"], "executable": "yay", "sudo_password": "p a's$"},
            )
        self.assertFalse(result.failed)
        self.assertEqual(
            seen["command"],
            ["yay", "--sudoflags", "-A", "-S", "--needed", "--noconfirm", "--", "new"],
        )
        self.assertEqual(seen["output"], "p a's$\n")
        self.assertEqual(seen["mode"], 0o700)
        self.assertFalse(os.path.exists(seen["askpass"]))
        self.assertFalse(os.path.exists(os.path.dirname(seen["askpass"])))

    def test_aur_reports_partial_installation_on_failure(self):
        with patch.object(
            Module,
            "run_command",
            create=True,
            side_effect=[
                (0, "existing 1\n", ""),
                (127, "new\n", ""),
                (1, "", "failed"),
                (0, "existing 1\ndependency 2\n", ""),
                (127, "new\n", ""),
            ],
        ):
            result = self.invoke(aur, {"name": ["new"], "executable": "paru"})
        self.assertTrue(result.failed)
        self.assertEqual(result.data["changed_packages"], ["dependency"])

    def test_aur_idempotence_and_check_mode(self):
        for names, unsatisfied, check, expected in [
            (["existing"], (0, "", ""), False, False),
            (["new"], (127, "new\n", ""), True, True),
        ]:
            with patch.object(
                Module,
                "run_command",
                create=True,
                side_effect=[(0, "existing 1\n", ""), unsatisfied],
            ) as run:
                result = self.invoke(
                    aur, {"name": names, "executable": "yay"}, check=check
                )
            self.assertFalse(result.failed)
            self.assertEqual(result.data["changed"], expected)
            self.assertEqual(
                [call.args[0][0] for call in run.call_args_list], ["pacman", "pacman"]
            )

    def test_aur_accepts_a_name_satisfied_by_another_package(self):
        # foo-git provides foo: pacman -T reports nothing unsatisfied.
        with patch.object(
            Module,
            "run_command",
            create=True,
            side_effect=[(0, "foo-git 1\n", ""), (0, "", "")],
        ) as run:
            result = self.invoke(aur, {"name": ["foo"], "executable": "yay"})
        self.assertFalse(result.failed)
        self.assertFalse(result.data["changed"])
        self.assertEqual(len(run.call_args_list), 2)

    def test_aur_fails_when_pacman_cannot_check_dependencies(self):
        with patch.object(
            Module,
            "run_command",
            create=True,
            side_effect=[(0, "existing 1\n", ""), (1, "", "database locked")],
        ):
            result = self.invoke(aur, {"name": ["new"], "executable": "yay"})
        self.assertTrue(result.failed)
        self.assertIn("database locked", result.data["msg"])

    def test_aur_rejects_option_like_names_before_running_commands(self):
        with patch.object(Module, "run_command", create=True) as run:
            result = self.invoke(aur, {"name": ["--evil"], "executable": "yay"})
        self.assertTrue(result.failed)
        run.assert_not_called()

    def test_tree_hidden_empty_dangling_and_cyclic_links(self):
        (self.root / ".hidden").write_text("hidden")
        (self.root / "empty").mkdir()
        (self.root / "alias").symlink_to(".hidden")
        (self.root / "cycle").symlink_to(".")
        (self.root / "broken").symlink_to("missing")
        entries = {
            Path(entry["path"]).name: entry for entry in tree.collect(str(self.root))
        }
        self.assertEqual(len(entries), 6)
        self.assertTrue(entries[".hidden"]["isreg"])
        self.assertTrue(entries["empty"]["isdir"])
        self.assertTrue(entries["alias"]["isreg"])
        self.assertTrue(entries["cycle"]["islnk"])
        self.assertEqual(entries["broken"]["lnk_target"], "missing")
        self.assertNotIn("dest", entries[".hidden"])

    def test_tree_dest_maps_each_entry_under_the_destination(self):
        (self.root / "sub").mkdir()
        (self.root / "sub/file").write_text("file")
        entries = {
            os.path.relpath(entry["path"], self.root): entry["dest"]
            for entry in tree.collect(str(self.root), dest="/home/user/./.vim/")
        }
        self.assertEqual(
            entries,
            {
                ".": "/home/user/.vim",
                "sub": "/home/user/.vim/sub",
                "sub/file": "/home/user/.vim/sub/file",
            },
        )

    def test_tree_tracked_copies_git_files_and_refuses_submodules(self):
        parent = self.root / "parent"
        repository(parent)
        source = parent / "home/.vim"
        (source / "config").mkdir(parents=True)
        (source / "config/plugins.vim").write_text("tracked")
        (parent / ".gitignore").write_text("backup/\n")
        git(parent, "add", ".")
        git(parent, "commit", "-m", "tree")
        # What a program writes into the tree, as Vim did into the old clone.
        (source / "backup").mkdir()
        (source / "backup/file~").write_text("ignored")
        (source / "untracked").write_text("untracked")
        (source / "bundle/gruvbox").mkdir(parents=True)
        git(source / "bundle/gruvbox", "init")

        files = tree.collect(str(source), tracked=True, dest="/h/.vim")
        entries = {os.path.relpath(entry["path"], source): entry for entry in files}
        self.assertEqual(set(entries), {".", "config", "config/plugins.vim"})
        self.assertEqual(
            entries["config/plugins.vim"]["checksum"],
            hashlib.sha1(b"tracked").hexdigest(),
        )
        self.assertNotIn("checksum", entries["config"])
        # Without the option, the same tree lists everything on disk.
        everything = {
            os.path.relpath(entry["path"], source)
            for entry in tree.collect(str(source))
        }
        self.assertIn("backup/file~", everything)
        self.assertIn("bundle/gruvbox/.git", everything)

        # A submodule's files would not be copied, so the module refuses it
        # even when it is not checked out.
        plugin = self.root / "plugin"
        repository(plugin)
        (plugin / "plugin.zsh").write_text("plugin")
        git(plugin, "add", ".")
        git(plugin, "commit", "-m", "plugin")
        git(
            parent,
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            str(plugin),
            "home/.vim/plugins/one",
        )
        git(parent, "submodule", "deinit", "--force", "home/.vim/plugins/one")
        failed = self.invoke(tree, {"path": str(source), "tracked": True, "dest": None})
        self.assertTrue(failed.failed)
        self.assertIn(
            f"Submodule in a copied tree: {source / 'plugins/one'}", failed.data["msg"]
        )
        # Outside a Git repository the module fails instead of copying nothing.
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "file").write_text("file")
        failed = self.invoke(
            tree, {"path": str(outside), "tracked": True, "dest": None}
        )
        self.assertTrue(failed.failed)
        self.assertIn("cannot list Git-tracked files", failed.data["msg"])

    def test_tree_tracked_keeps_the_files_behind_a_tracked_directory_link(self):
        parent = self.root / "linked"
        repository(parent)
        (parent / "shared").mkdir()
        (parent / "shared/lib.zsh").write_text("shared")
        source = parent / "home/zsh"
        source.mkdir(parents=True)
        (source / "lib").symlink_to("../../shared")
        git(parent, "add", ".")
        git(parent, "commit", "-m", "tree")

        files = tree.collect(str(source), tracked=True, dest="/h/zsh")
        entries = {os.path.relpath(entry["path"], source): entry for entry in files}
        # Git tracks only the link, yet the copy follows it to a directory.
        self.assertEqual(set(entries), {".", "lib", "lib/lib.zsh"})
        self.assertTrue(entries["lib"]["isdir"])
        self.assertEqual(entries["lib/lib.zsh"]["dest"], "/h/zsh/lib/lib.zsh")

    def test_backup_preserves_inode_modes_hardlinks_and_broken_links(self):
        src, dest = self.root / "source", self.root / "backup"
        src.mkdir(mode=0o700)
        (src / "data").write_text("original")
        os.link(src / "data", src / "hardlink")
        (src / "broken").symlink_to("missing")
        inode = src.stat().st_ino
        planned = self.invoke(backup, {"src": str(src), "dest": str(dest)}, check=True)
        self.assertFalse(planned.failed)
        self.assertTrue(src.exists())
        result = self.invoke(backup, {"src": str(src), "dest": str(dest)})
        self.assertFalse(result.failed)
        self.assertFalse(src.exists())
        self.assertEqual(dest.stat().st_ino, inode)
        self.assertEqual(dest.stat().st_mode & 0o777, 0o700)
        self.assertEqual(
            (dest / "data").stat().st_ino, (dest / "hardlink").stat().st_ino
        )
        self.assertTrue((dest / "broken").is_symlink())
        self.assertIn(str(dest / "data"), result.data["changed_files"])

    def test_backup_refuses_existing_destination_even_during_rename(self):
        src, dest = self.root / "source", self.root / "backup"
        src.write_text("source")
        dest.write_text("backup")
        with self.assertRaises(FileExistsError):
            files.move_without_replace(str(src), str(dest))
        self.assertEqual(src.read_text(), "source")
        self.assertEqual(dest.read_text(), "backup")

    def test_snapshot_reports_modes_links_and_deletions(self):
        data = self.root / "data"
        data.write_text("content")
        link = self.root / "link"
        link.symlink_to("missing")
        before = files.snapshot([str(self.root)])
        data.chmod(0o600)
        link.unlink()
        after = files.snapshot([str(self.root)])
        changed = files.changed_paths(before, after)
        self.assertIn(str(data), changed)
        self.assertIn(str(link), changed)

    def test_snapshot_propagates_unreadable_tree(self):
        with (
            patch.object(files.os, "scandir", side_effect=PermissionError("denied")),
            self.assertRaises(PermissionError),
        ):
            files.snapshot([str(self.root)])

    def test_real_sysfs_module_check_write_and_idempotence(self):
        control = self.root / "control"
        control.write_text("performance\n")
        real_open = open

        def redirected(path, *args, **kwargs):
            self.assertEqual(path, "/sys/test/control")
            return real_open(control, *args, **kwargs)

        with patch("builtins.open", side_effect=redirected):
            params = {"path": "/sys/test/control", "value": "powersave"}
            planned = self.invoke(sysfs, params, check=True)
            self.assertTrue(planned.data["changed"])
            with real_open(control) as stream:
                self.assertEqual(stream.read(), "performance\n")
            result = self.invoke(sysfs, params)
            self.assertFalse(result.failed)
            self.assertEqual(result.data["changed_files"], ["/sys/test/control"])
            self.assertFalse(self.invoke(sysfs, params).data["changed"])

    def test_sysfs_refuses_non_sysfs_path(self):
        result = self.invoke(sysfs, {"path": str(self.root / "control"), "value": "x"})
        self.assertTrue(result.failed)
        self.assertFalse((self.root / "control").exists())

    def test_sysfs_write_failure_reports_attempted_path(self):
        from io import StringIO

        with patch(
            "builtins.open", side_effect=[StringIO("old"), OSError("write failed")]
        ):
            result = self.invoke(sysfs, {"path": "/sys/test/control", "value": "new"})
        self.assertTrue(result.failed)
        self.assertTrue(result.data["changed"])
        self.assertEqual(result.data["changed_files"], ["/sys/test/control"])

    def test_sysfs_readback_mismatch_fails(self):
        from io import StringIO

        with patch(
            "builtins.open", side_effect=[StringIO("old"), StringIO(), StringIO("old")]
        ):
            result = self.invoke(sysfs, {"path": "/sys/test/control", "value": "new"})
        self.assertTrue(result.failed)
        self.assertIn("read back", result.data["msg"])

    def test_initramfs_reports_custom_output_and_failure(self):
        target = self.root / "image"

        def generate(*args, **kwargs):
            target.write_text("new")
            raise subprocess.CalledProcessError(1, ["generator"])

        with patch.object(initramfs.subprocess, "run", side_effect=generate):
            result = self.invoke(
                initramfs, {"generator": "dracut", "report_roots": [str(self.root)]}
            )
        self.assertTrue(result.failed)
        self.assertIn(str(target), result.data["changed_files"])

    def test_generators_check_mode_never_execute(self):
        for implementation, params in [
            (initramfs, {"generator": "dracut", "report_roots": [str(self.root)]}),
            (makepkg, {"path": str(self.root)}),
        ]:
            with patch.object(implementation.subprocess, "run") as run:
                self.assertFalse(self.invoke(implementation, params, check=True).failed)
                run.assert_not_called()

    def test_makepkg_controls_output_locations(self):
        def build(*args, **kwargs):
            for key in ["PKGDEST", "SRCDEST", "SRCPKGDEST", "LOGDEST", "BUILDDIR"]:
                self.assertEqual(kwargs["env"][key], str(self.root))
            (self.root / "yay.pkg.tar.zst").write_text("package")
            return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

        with patch.object(makepkg.subprocess, "run", side_effect=build):
            result = self.invoke(makepkg, {"path": str(self.root)})
        self.assertFalse(result.failed)
        self.assertIn(str(self.root / "yay.pkg.tar.zst"), result.data["changed_files"])


class RetiredPluginsTests(unittest.TestCase):
    """Only work that exists nowhere else stops the removal of a clone."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.upstream = self.root / "upstream"
        repository(self.upstream)
        (self.upstream / "plugin.vim").write_text("v1\n")
        git(self.upstream, "add", ".")
        git(self.upstream, "commit", "-q", "-m", "v1")

    def clone(self, name):
        path = self.root / name
        git(self.root, "clone", "-q", f"file://{self.upstream}", str(path))
        for key, value in (
            ("user.name", "Test"),
            ("user.email", "test@example.invalid"),
            ("commit.gpgsign", "false"),
        ):
            git(path, "config", key, value)
        return path

    def test_clean_and_detached_clones_hold_no_local_work(self):
        self.assertEqual(retired.local_work(str(self.clone("clean"))), [])
        detached = self.clone("detached")
        git(detached, "checkout", "-q", "--detach", "HEAD")
        self.assertEqual(retired.local_work(str(detached)), [])

    def test_stash_and_commits_without_a_remote_are_local_work(self):
        stashed = self.clone("stashed")
        (stashed / "plugin.vim").write_text("edit\n")
        git(stashed, "stash", "push", "-q", "-m", "test")
        self.assertEqual(git(stashed, "status", "--porcelain"), "")
        self.assertEqual(retired.local_work(str(stashed)), ["a stash"])

        # A branch other than the one checked out counts too.
        branched = self.clone("branched")
        git(branched, "checkout", "-q", "-b", "local")
        git(branched, "commit", "-q", "--allow-empty", "-m", "local")
        git(branched, "checkout", "-q", "-")
        self.assertEqual(
            retired.local_work(str(branched)), ["commits that no remote branch holds"]
        )
        self.assertEqual(
            retired.local_work(str(self.upstream)),
            ["commits that no remote branch holds"],
        )

    def test_unreadable_repository_is_reported_rather_than_removed(self):
        broken = self.clone("broken")
        (broken / ".git/HEAD").write_text("garbage\n")
        with self.assertRaises(retired.LocalWork):
            retired.local_work(str(broken))

    def test_nested_repositories_are_found_without_entering_git_directories(self):
        outer = self.clone("bundle/outer")
        inner = outer / "deps/inner"
        repository(inner)
        (self.root / "bundle/plain").mkdir()
        self.assertEqual(
            retired.repositories(str(self.root / "bundle")), [str(outer), str(inner)]
        )

    def test_paths_must_stay_under_the_home(self):
        for path in ("../escape", "/etc", ".vim/../../escape"):
            with self.subTest(path), self.assertRaises(ValueError):
                retired.plan(str(self.root), [path], [])


class RetiredPluginsBackupTests(unittest.TestCase):
    """What is not a Git clone is never deleted: it moves to <path>.bak."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.upstream = self.root / "upstream"
        repository(self.upstream)
        (self.upstream / "plugin.vim").write_text("v1\n")
        git(self.upstream, "add", ".")
        git(self.upstream, "commit", "-q", "-m", "v1")

    def clone(self, relative):
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        git(self.root, "clone", "-q", f"file://{self.upstream}", str(path))
        return path

    def run_module(self, paths, parents=(), check=False):
        params = {
            "home": str(self.home),
            "paths": list(paths),
            "parents": list(parents),
        }
        with (
            patch.object(retired, "AnsibleModule", return_value=Module(params, check)),
            self.assertRaises(Result) as caught,
        ):
            retired.main()
        return caught.exception

    def tree(self):
        return sorted(
            (str(item.relative_to(self.home)), item.is_symlink())
            for item in self.home.rglob("*")
        )

    def test_a_file_beside_the_clones_moves_the_whole_path_to_a_backup(self):
        bundle = self.home / ".vim/bundle"
        self.clone(".vim/bundle/gruvbox")
        (bundle / ".netrwhist").write_text("history\n")
        before = self.tree()

        planned = self.run_module([".vim/bundle"], check=True)
        self.assertFalse(planned.failed, planned.data)
        self.assertEqual(planned.data["backed_up"], [str(bundle)])
        self.assertEqual(planned.data["removed"], [])
        self.assertTrue(planned.data["changed"])
        self.assertEqual(self.tree(), before)

        done = self.run_module([".vim/bundle"])
        self.assertFalse(done.failed, done.data)
        self.assertFalse(bundle.exists())
        backup = self.home / ".vim/bundle.bak"
        self.assertEqual((backup / ".netrwhist").read_text(), "history\n")
        self.assertEqual((backup / "gruvbox/plugin.vim").read_text(), "v1\n")

        # Nothing left to do: the backup itself is not a listed path.
        again = self.run_module([".vim/bundle"])
        self.assertFalse(again.data["changed"])

    def test_a_file_inside_a_plain_directory_is_backed_up(self):
        (self.home / ".vim/bundle/handmade/plugin").mkdir(parents=True)
        (self.home / ".vim/bundle/handmade/plugin/mine.vim").write_text("mine\n")
        self.run_module([".vim/bundle"])
        self.assertEqual(
            (self.home / ".vim/bundle.bak/handmade/plugin/mine.vim").read_text(),
            "mine\n",
        )

    def test_a_regular_file_at_the_path_is_backed_up(self):
        (self.home / ".vim").mkdir()
        (self.home / ".vim/bundle").write_text("not a directory\n")
        result = self.run_module([".vim/bundle"])
        self.assertEqual(result.data["backed_up"], [str(self.home / ".vim/bundle")])
        self.assertEqual(
            (self.home / ".vim/bundle.bak").read_text(), "not a directory\n"
        )

    def test_a_link_beside_the_clones_is_backed_up_and_not_followed(self):
        target = self.root / "elsewhere"
        target.mkdir()
        (target / "keep").write_text("keep\n")
        self.clone(".vim/bundle/gruvbox")
        (self.home / ".vim/bundle/linked").symlink_to(target)
        self.run_module([".vim/bundle"])
        self.assertTrue((self.home / ".vim/bundle.bak/linked").is_symlink())
        self.assertEqual((target / "keep").read_text(), "keep\n")

    def test_clean_clones_and_empty_directories_are_removed_without_backup(self):
        self.clone(".vim/bundle/gruvbox")
        (self.home / ".vim/bundle/empty/nested").mkdir(parents=True)
        result = self.run_module([".vim/bundle"])
        self.assertFalse(result.failed, result.data)
        self.assertEqual(result.data["removed"], [str(self.home / ".vim/bundle")])
        self.assertEqual(result.data["backed_up"], [])
        self.assertFalse(os.path.lexists(self.home / ".vim/bundle"))
        self.assertFalse(os.path.lexists(self.home / ".vim/bundle.bak"))

    def test_an_existing_backup_stops_everything(self):
        (self.home / ".vim/bundle").mkdir(parents=True)
        (self.home / ".vim/bundle/.netrwhist").write_text("history\n")
        (self.home / ".vim/bundle.bak").mkdir()
        (self.home / ".vim/bundle.bak/old").write_text("old\n")
        self.clone(".tmux/plugins/tpm")
        before = self.tree()
        for check in (True, False):
            with self.subTest(check=check):
                result = self.run_module(
                    [".vim/bundle", ".tmux/plugins"], [".tmux"], check=check
                )
                self.assertTrue(result.failed)
                self.assertIn(str(self.home / ".vim/bundle.bak"), result.data["msg"])
                self.assertEqual(self.tree(), before)

    def test_local_work_still_stops_a_path_that_would_be_backed_up(self):
        clone = self.clone(".vim/bundle/gruvbox")
        (clone / "plugin.vim").write_text("edited\n")
        (self.home / ".vim/bundle/.netrwhist").write_text("history\n")
        before = self.tree()
        result = self.run_module([".vim/bundle"])
        self.assertTrue(result.failed)
        self.assertIn("uncommitted changes", result.data["msg"])
        self.assertEqual(self.tree(), before)

    def test_a_parent_keeping_a_backup_is_reported_with_it(self):
        self.clone(".tmux/plugins/tpm")
        (self.home / ".tmux/plugins/notes").write_text("notes\n")
        warnings = []
        with patch.object(Module, "warn", warnings.append, create=True):
            result = self.run_module([".tmux/plugins"], [".tmux"])
        self.assertEqual(result.data["kept"], [str(self.home / ".tmux")])
        self.assertIn("plugins.bak", warnings[0])
        self.assertTrue((self.home / ".tmux/plugins.bak/notes").exists())

    def test_an_emptied_parent_is_removed(self):
        self.clone(".tmux/plugins/tpm")
        result = self.run_module([".tmux/plugins"], [".tmux"])
        self.assertFalse(os.path.lexists(self.home / ".tmux"))
        self.assertIn(str(self.home / ".tmux"), result.data["removed"])

    def test_a_link_at_the_path_loses_the_link_only(self):
        target = self.root / "clone-tmux"
        target.mkdir()
        (target / "resurrect").write_text("session\n")
        (self.home / ".tmux").symlink_to(target)
        result = self.run_module([".tmux/plugins"], [".tmux"])
        self.assertEqual(result.data["removed"], [str(self.home / ".tmux")])
        self.assertFalse(os.path.lexists(self.home / ".tmux"))
        self.assertEqual((target / "resurrect").read_text(), "session\n")

    def test_a_path_below_an_unlisted_link_is_skipped(self):
        target = self.root / "vim"
        (target / "bundle").mkdir(parents=True)
        (self.home / ".vim").symlink_to(target)
        result = self.run_module([".vim/bundle"])
        self.assertFalse(result.data["changed"])
        self.assertEqual(len(result.data["skipped"]), 1)
        self.assertTrue((target / "bundle").is_dir())

    def test_a_path_outside_the_home_fails(self):
        result = self.run_module(["../escape"])
        self.assertTrue(result.failed)
