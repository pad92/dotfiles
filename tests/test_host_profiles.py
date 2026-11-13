"""Per-host settings: host_vars/<hostname>.yml of the SSH inventory."""

import platform
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from ansible_host_profiles import (
    INVENTORY,
    ROOT,
    UNSET,
    configured_hostnames,
    inventory_arguments,
    resolve_host_settings,
)
from ansible_test_environment import ansible_test_environment, ansible_tree

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
        return resolve_host_settings(hostname, self.work)[0]

    # The ignored local Vault is encrypted on a workstation: the tests have no
    # password for it, and CI has no such file.
    def test_ansible_copy_leaves_out_the_local_vault(self):
        source = self.work / "source"
        (source / "group_vars/all").mkdir(parents=True)
        (source / "group_vars/all/vault.yml").write_text("$ANSIBLE_VAULT;1.1;AES256\n")
        (source / "group_vars/all/main.yml").write_text("x: 1\n")
        (source / "host_vars").mkdir()
        (source / "inventory.yml").write_text("all: {}\n")
        (source / "roles").mkdir()

        tree = ansible_tree(self.work / "out", source)

        self.assertFalse(list(tree.glob("group_vars/*/vault*.yml")))
        self.assertTrue((tree / "group_vars/all/main.yml").is_file())
        self.assertFalse((tree / "inventory.yml").is_symlink())
        self.assertTrue((tree / "roles").is_symlink())

    def test_laptop_adds_the_vpn_and_disables_ipv6_and_hypridle(self):
        settings = self.settings("PadsP5560")
        self.assertEqual(settings["packages_host_groups"], WORKSTATION + ["23_vpn"])
        self.assertIs(settings["hardening_ipv6_enabled"], False)
        self.assertIs(settings["dotfiles_hypridle_enabled"], False)

    def test_tower_adds_steam_and_keeps_the_ipv6_default(self):
        settings = self.settings("PadsTower")
        self.assertEqual(settings["packages_host_groups"], WORKSTATION + ["21_steam"])
        self.assertEqual(settings["hardening_ipv6_enabled"], UNSET)
        self.assertIs(settings["dotfiles_hypridle_enabled"], False)

    # A fresh machine must not inherit a known host's packages or settings.
    def test_unknown_host_keeps_every_role_default(self):
        settings = self.settings("fresh-box")
        for name in [
            "packages_host_groups",
            "hardening_ipv6_enabled",
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

    # A host_vars file without an inventory entry would never be applied.
    def test_inventory_lists_exactly_the_hosts_with_settings(self):
        hosts = yaml.safe_load(INVENTORY.read_text())["all"]["hosts"]
        self.assertEqual(sorted(hosts), configured_hostnames())
        for hostname, variables in hosts.items():
            with self.subTest(host=hostname):
                self.assertNotIn("ansible_connection", variables or {})

    def test_playbooks_gather_user_facts_and_check_the_target_first(self):
        for playbook in ["site.yml", "obs.yml"]:
            play = yaml.safe_load((ROOT / "ansible" / playbook).read_text())[0]
            step = next(
                task
                for task in play["pre_tasks"]
                if task.get("ansible.builtin.import_tasks") == "tasks/target.yml"
            )
            with self.subTest(playbook=playbook):
                self.assertEqual(play["hosts"], "all")
                self.assertIs(play["gather_facts"], False)
                self.assertEqual(step["tags"], ["always"])

    def check_target(self, hostname):
        """Run tasks/target.yml locally for an inventory name."""
        playbook = self.work / "target.yml"
        playbook.write_text(
            yaml.safe_dump(
                [
                    {
                        "hosts": hostname,
                        "gather_facts": False,
                        "vars": {"workstation_fact_subset": ["min"]},
                        "tasks": [
                            {
                                "ansible.builtin.import_tasks": str(
                                    ROOT / "ansible/tasks/target.yml"
                                )
                            }
                        ],
                    }
                ]
            )
        )
        return subprocess.run(
            [
                "ansible-playbook",
                *inventory_arguments(hostname, self.work),
                str(playbook),
            ],
            cwd=self.work,
            env=ansible_test_environment(self.work),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    # host_vars name a machine: applying them to another one must fail early.
    def test_target_check_refuses_a_machine_with_another_hostname(self):
        result = self.check_target("fresh-box")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reached a machine named", result.stdout)

    def test_target_check_gathers_the_facts_of_the_ssh_user(self):
        hostname = platform.node().split(".")[0]
        result = self.check_target(hostname)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("reached a machine named", result.stdout)


if __name__ == "__main__":
    unittest.main()
