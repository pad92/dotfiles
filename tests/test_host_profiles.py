"""Per-host settings: group_vars/host_<hostname>.yml loaded through group_by."""

import shutil
import tempfile
import unittest
from pathlib import Path

import yaml
from ansible_host_profiles import (
    ROOT,
    UNSET,
    configured_hostnames,
    resolve_host_settings,
)

WORKSTATION = yaml.safe_load(
    (ROOT / "ansible/group_vars/all/packages.yml").read_text()
)["packages_workstation_groups"]
ARCH_GROUPS = yaml.safe_load(
    (ROOT / "ansible/roles/packages/vars/archlinux.yml").read_text()
)["packages_family_groups"]["Archlinux"]


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
class HostProfileTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)

    def settings(self, hostname):
        settings, warnings = resolve_host_settings(hostname, self.work)
        self.assertNotIn("Invalid characters", warnings)
        return settings

    def test_laptop_adds_the_vpn_and_disables_ipv6_and_hypridle(self):
        settings = self.settings("PadsP5560")
        self.assertIn("host_PadsP5560", settings["group_names"])
        self.assertEqual(settings["packages_host_groups"], WORKSTATION + ["23_vpn"])
        self.assertIs(settings["system_ipv6_enabled"], False)
        self.assertIs(settings["dotfiles_hypridle_enabled"], False)

    def test_tower_adds_steam_and_keeps_the_ipv6_default(self):
        settings = self.settings("PadsTower")
        self.assertEqual(settings["packages_host_groups"], WORKSTATION + ["21_steam"])
        self.assertEqual(settings["system_ipv6_enabled"], UNSET)
        self.assertIs(settings["dotfiles_hypridle_enabled"], False)

    # A fresh machine must not inherit a known host's packages or settings.
    def test_unknown_host_keeps_every_role_default(self):
        settings = self.settings("fresh-box")
        self.assertIn("host_fresh_box", settings["group_names"])
        for name in [
            "packages_host_groups",
            "system_ipv6_enabled",
            "dotfiles_hypridle_enabled",
        ]:
            with self.subTest(setting=name):
                self.assertEqual(settings[name], UNSET)

    # A typo in a group name would otherwise fail only on that machine.
    def test_every_host_selects_existing_arch_groups(self):
        hostnames = configured_hostnames()
        self.assertEqual(hostnames, ["PadsP5560", "PadsTower"])
        for hostname in hostnames:
            with self.subTest(host=hostname):
                groups = self.settings(hostname)["packages_host_groups"]
                self.assertEqual(sorted(set(groups) - set(ARCH_GROUPS)), [])
                self.assertEqual(len(groups), len(set(groups)))

    def test_playbooks_load_the_host_settings_before_their_roles(self):
        for playbook in ["site.yml", "obs.yml"]:
            play = yaml.safe_load((ROOT / "ansible" / playbook).read_text())[0]
            step = next(
                task
                for task in play["pre_tasks"]
                if task.get("ansible.builtin.import_tasks") == "tasks/host_profile.yml"
            )
            with self.subTest(playbook=playbook):
                self.assertEqual(step["tags"], ["always"])


if __name__ == "__main__":
    unittest.main()
