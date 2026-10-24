"""Exercise production modules against temporary files and mocked system boundaries."""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
submodules = load("submodules_module", "ansible/library/dotfiles_submodule_update.py")
sysfs = load("sysfs_module", "ansible/library/dotfiles_sysfs.py")
initramfs = load("initramfs_module", "ansible/library/dotfiles_initramfs.py")
makepkg = load("makepkg_module", "ansible/library/dotfiles_makepkg.py")

tree = load("tree_module", "ansible/library/dotfiles_tree.py")

aur = load("aur_module", "ansible/library/dotfiles_aur.py")


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
                (0, "", ""),
                (0, "existing 1\nnew 2\n", ""),
            ],
        ) as run:
            result = self.invoke(
                aur, {"name": ["existing", "new"], "executable": "yay"}
            )
        self.assertFalse(result.failed)
        self.assertEqual(result.data["changed_packages"], ["new"])
        self.assertEqual(
            run.call_args_list[1].args[0],
            ["yay", "-S", "--needed", "--noconfirm", "--", "new"],
        )

    def test_aur_reports_partial_installation_on_failure(self):
        with patch.object(
            Module,
            "run_command",
            create=True,
            side_effect=[
                (0, "existing 1\n", ""),
                (1, "", "failed"),
                (0, "existing 1\ndependency 2\n", ""),
            ],
        ):
            result = self.invoke(aur, {"name": ["new"], "executable": "paru"})
        self.assertTrue(result.failed)
        self.assertEqual(result.data["changed_packages"], ["dependency"])

    def test_aur_idempotence_and_check_mode(self):
        for names, check, expected in [
            (["existing"], False, False),
            (["new"], True, True),
        ]:
            with patch.object(
                Module, "run_command", create=True, return_value=(0, "existing 1\n", "")
            ) as run:
                result = self.invoke(
                    aur, {"name": names, "executable": "yay"}, check=check
                )
            self.assertFalse(result.failed)
            self.assertEqual(result.data["changed"], expected)
            run.assert_called_once_with(["pacman", "-Q"])

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
            backup.move_without_replace(str(src), str(dest))
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

    def test_submodule_paths_with_spaces_initialization_and_update(self):
        def git(path, *args):
            return subprocess.run(
                ["git", "-C", str(path), *args],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

        child, parent = self.root / "child", self.root / "parent"
        for path in [child, parent]:
            path.mkdir()
            git(path, "init")
            git(path, "config", "commit.gpgsign", "false")
            git(path, "config", "user.name", "Test")
            git(path, "config", "user.email", "test@example.invalid")
        (child / "file name").write_text("one")
        git(child, "add", ".")
        git(child, "commit", "-m", "first")
        git(
            parent,
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            str(child),
            "sub module",
        )
        first = submodules.submodule_revisions(str(parent))
        self.assertEqual(list(first), ["sub module"])
        (child / "file name").write_text("two")
        git(child, "commit", "-am", "second")
        git(parent / "sub module", "fetch")
        git(parent / "sub module", "checkout", git(child, "rev-parse", "HEAD"))
        second = submodules.submodule_revisions(str(parent))
        changed = submodules.changed_submodule_files(str(parent), first, second)
        self.assertEqual(changed, [str(parent / "sub module/file name")])
        planned = self.invoke(submodules, {"path": str(parent)}, check=True)
        self.assertTrue(planned.data["changed"])
        result = self.invoke(submodules, {"path": str(parent)})
        self.assertFalse(result.failed)
        self.assertEqual(result.data["changed_files"], changed)
        self.assertFalse(self.invoke(submodules, {"path": str(parent)}).data["changed"])
