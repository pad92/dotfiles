import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts/ansible_backup_files.py"
SPEC = importlib.util.spec_from_file_location("ansible_backups", SCRIPT)
backups = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backups)


class AnsibleBackupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home"
        self.home.mkdir()

    def config(self, **overrides):
        defaults = backups.DataLoader().load_from_file(
            str(backups.DOTFILES_DEFAULTS), trusted_as_template=True
        )
        variables = {
            **defaults,
            "dotfiles_home": str(self.home),
            **overrides,
        }
        templar = backups.Templar(loader=backups.DataLoader(), variables=variables)
        return {
            name: templar.template(variables[name]) for name in backups.PATH_VARIABLES
        }

    def test_finds_only_exact_managed_backups(self):
        managed = self.home / ".zshrc.123.2026-10-16@12:00:00~"
        managed.write_text("backup")
        unmanaged = self.home / "unmanaged.123.2026-10-16@12:00:00~"
        unmanaged.write_text("keep")
        result = backups.find_backups(self.home, self.config())
        self.assertEqual(result, [managed])

    def test_finds_conflict_backup_but_not_through_symlink_parent(self):
        backup = self.home / ".zshrc.bak"
        backup.write_text("backup")
        linked = self.home / ".config"
        linked.symlink_to(self.root, target_is_directory=True)
        unsafe = self.root / "waybar" / "config.bak"
        unsafe.parent.mkdir()
        unsafe.write_text("keep")
        result = backups.find_backups(self.home, self.config())
        self.assertIn(backup, result)
        self.assertNotIn(unsafe, result)

    def test_rejects_paths_escaping_home(self):
        with self.assertRaises(ValueError):
            backups.validate_relative_path("../outside")
        with self.assertRaises(ValueError):
            backups.validate_relative_path("/tmp/outside")

    def test_removes_files_and_directories_only_after_selection(self):
        file_backup = self.home / ".zshrc.bak"
        file_backup.write_text("backup")
        directory_backup = self.home / ".bin.bak"
        directory_backup.mkdir()
        (directory_backup / "old-file").write_text("backup")
        backups.remove_backups([file_backup, directory_backup])
        self.assertFalse(file_backup.exists())
        self.assertFalse(directory_backup.exists())

    def test_removes_symlink_without_following_target(self):
        target = self.root / "keep"
        target.write_text("keep")
        link = self.home / ".zshrc.bak"
        link.symlink_to(target)
        backups.remove_backups([link])
        self.assertFalse(link.exists())
        self.assertTrue(target.exists())


if __name__ == "__main__":
    unittest.main()
