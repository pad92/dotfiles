"""Tests for the iwlwifi role, which owns /etc/modprobe.d/iwlwifi.conf."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from ansible_test_environment import ansible_test_environment

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "ansible/roles/iwlwifi"
POWER_SCHEME = [{"module": "iwlmvm", "options": ["power_scheme=1"]}]


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
class IwlwifiRoleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.modules = self.work / "module"
        (self.modules / "iwlwifi").mkdir(parents=True)
        self.target = self.work / "etc/iwlwifi.conf"
        self.target.parent.mkdir()
        self.vendor = self.work / "usr/iwlwifi.conf"

    def run_role(self, expect_success=True, **extra_vars):
        tasks = yaml.safe_load((ROLE / "tasks/main.yml").read_text())
        templates = [
            task["ansible.builtin.template"]
            for block in tasks
            for task in [block, *block.get("block", [])]
            if "ansible.builtin.template" in task
        ]
        # Guard the rewrite below: the role must still write through a template.
        self.assertEqual(len(templates), 1)
        templates[0]["src"] = str(ROLE / "templates" / templates[0]["src"])
        templates[0].pop("owner")
        templates[0].pop("group")
        playbook = self.work / "play.yml"
        playbook.write_text(
            yaml.safe_dump(
                [
                    {
                        "hosts": "localhost",
                        "connection": "local",
                        "gather_facts": False,
                        "vars": {
                            **yaml.safe_load((ROLE / "defaults/main.yml").read_text()),
                            "iwlwifi_modprobe_path": str(self.target),
                            "iwlwifi_vendor_modprobe_path": str(self.vendor),
                            "iwlwifi_module_directory": str(self.modules),
                            **extra_vars,
                        },
                        "tasks": tasks,
                        "handlers": yaml.safe_load(
                            (ROLE / "handlers/main.yml").read_text()
                        ),
                    }
                ]
            )
        )
        result = subprocess.run(
            ["ansible-playbook", "-i", "localhost,", str(playbook)],
            cwd=ROOT,
            env=ansible_test_environment(self.work),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode == 0, expect_success, output)
        return output

    def options(self):
        return [
            line
            for line in self.target.read_text().splitlines()
            if not line.startswith("#")
        ]

    def backups(self):
        return [path for path in self.target.parent.iterdir() if path != self.target]

    def test_writes_the_listed_options(self):
        output = self.run_role(
            iwlwifi_module_options=[
                {"module": "iwlwifi", "options": ["power_save=0", "11n_disable=8"]},
                *POWER_SCHEME,
            ]
        )
        self.assertEqual(
            self.options(),
            [
                "options iwlwifi power_save=0 11n_disable=8",
                "options iwlmvm power_scheme=1",
            ],
        )
        self.assertIn("RUNNING HANDLER", output)

    def test_second_run_changes_nothing(self):
        self.run_role(iwlwifi_module_options=POWER_SCHEME)
        output = self.run_role(iwlwifi_module_options=POWER_SCHEME)
        self.assertIn("changed=0", output)
        self.assertEqual(self.backups(), [])

    def test_hand_written_file_is_replaced_with_a_backup(self):
        manual = "options iwlwifi power_save=0 swcrypto=1 bt_coex_active=0\n"
        self.target.write_text(manual)
        self.run_role(iwlwifi_module_options=POWER_SCHEME)
        self.assertEqual(self.options(), ["options iwlmvm power_scheme=1"])
        backups = self.backups()
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), manual)

    def test_unset_options_leave_the_file_alone(self):
        self.target.write_text("options iwlwifi power_save=0\n")
        self.run_role()
        self.assertEqual(self.target.read_text(), "options iwlwifi power_save=0\n")

    def test_empty_list_removes_the_file(self):
        self.target.write_text("options iwlwifi power_save=0\n")
        self.run_role(iwlwifi_module_options=[])
        self.assertFalse(self.target.exists())

    def test_absent_hardware_writes_nothing(self):
        (self.modules / "iwlwifi").rmdir()
        output = self.run_role(iwlwifi_module_options=POWER_SCHEME)
        self.assertFalse(self.target.exists())
        self.assertIn("iwlwifi is not loaded", output)

    def test_refuses_to_mask_a_vendor_file(self):
        self.vendor.parent.mkdir()
        self.vendor.write_text("options iwlwifi lar_disable=1\n")
        output = self.run_role(
            expect_success=False, iwlwifi_module_options=POWER_SCHEME
        )
        self.assertFalse(self.target.exists())
        self.assertIn(str(self.vendor), output)

    def test_refuses_to_fight_power_save_wifi(self):
        output = self.run_role(
            expect_success=False,
            iwlwifi_module_options=POWER_SCHEME,
            power_save_wifi=True,
        )
        self.assertFalse(self.target.exists())
        self.assertIn("power_save_wifi", output)

    def test_rejects_unknown_modules_and_malformed_options(self):
        for entry in (
            {"module": "e1000e", "options": ["SmartPowerDownEnable=1"]},
            {"module": "iwlwifi", "options": ["power_save"]},
            {"module": "iwlwifi", "options": ["power_save=0\ninstall iwlwifi /bin/sh"]},
        ):
            with self.subTest(entry=entry):
                self.run_role(expect_success=False, iwlwifi_module_options=[entry])
                self.assertFalse(self.target.exists())


if __name__ == "__main__":
    unittest.main()
