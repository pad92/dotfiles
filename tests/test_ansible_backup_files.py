import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ansible.parsing.vault import VaultLib, VaultSecret
from ansible_test_environment import ansible_test_environment, ansible_tree

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

    def test_backup_collector_has_no_removal_operation(self):
        self.assertFalse(hasattr(backups, "remove_backups"))


class InventoryWithVaultTests(unittest.TestCase):
    """load_configuration against a real ansible-inventory and a real Vault."""

    VAULT_PASSWORD = "test-only-vault-password"  # pragma: allowlist secret
    # A secret integer: ansible-core 2.22 masks Vault values in what it
    # displays, and a masked integer ($REDACTED$, unquoted) is not JSON.
    SECRET_PORT = 51820

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.home = self.work / "home"
        self.home.mkdir()
        ansible = ansible_tree(self.work)
        password_file = self.work / "vault-password"
        password_file.write_text(self.VAULT_PASSWORD)
        vault = VaultLib([("default", VaultSecret(self.VAULT_PASSWORD.encode()))])
        (ansible / "group_vars/all/vault.yml").write_bytes(
            vault.encrypt(
                f"vault_test_port: {self.SECRET_PORT}\n"
                "vault_test_host: vault-test.invalid\n"
            )
        )
        # The developer's own ANSIBLE_* settings (Vault identities, inventory)
        # must not reach this inventory: only the helper's settings apply.
        without_ansible = {
            name: value
            for name, value in os.environ.items()
            if not name.startswith("ANSIBLE_")
        }
        with patch.dict(os.environ, without_ansible, clear=True):
            environment = {
                **ansible_test_environment(self.work),
                "ANSIBLE_VAULT_PASSWORD_FILE": str(password_file),
            }
        patches = [
            patch.dict(os.environ, environment, clear=True),
            patch.object(backups, "REPOSITORY_ROOT", self.work),
        ]
        for active in patches:
            active.start()
            self.addCleanup(active.stop)

    def test_vault_integer_does_not_break_path_resolution(self):
        configuration = backups.load_configuration(self.home, [])

        self.assertEqual(
            set(configuration),
            set(backups.PATH_VARIABLES + backups.OBSOLETE_FILE_VARIABLES),
        )
        self.assertIn(".config/hypr", configuration["dotfiles_directories"])

    def test_extra_vars_still_override_group_vars(self):
        configuration = backups.load_configuration(
            self.home, ['{"dotfiles_files": [".custom-file"]}']
        )

        self.assertEqual(configuration["dotfiles_files"], [".custom-file"])


if __name__ == "__main__":
    unittest.main()
