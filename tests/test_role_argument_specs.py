"""Role argument specs: meta/argument_specs.yml of every role in ansible/roles.

Ansible validates a role's variables against its spec before the first task of
the role. The specs must declare every role default, so a default cannot slip
out of the documented interface, and they must accept the configuration of
every inventory host while refusing values the roles cannot use.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml
from ansible_host_profiles import configured_hostnames, inventory_arguments
from ansible_test_environment import (
    ROOT,
    ansible_test_environment,
    ansible_tree,
    run_playbook,
)

ROLES_DIR = ROOT / "ansible/roles"
SITE = ROOT / "ansible/site.yml"
VALIDATION_TASK = "Validating arguments against arg spec 'main'"
# Only the validation tasks carry the always tag inside the roles, so a tag
# that matches nothing runs them and skips the rest of each role.
NO_ROLE_TAG = "argument_spec_validation_only"


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text())


def role_names() -> list[str]:
    return sorted(path.name for path in ROLES_DIR.iterdir() if path.is_dir())


def site_play() -> dict[str, Any]:
    return load_yaml(SITE)[0]


def site_role_names() -> list[str]:
    return [entry["role"] for entry in site_play()["roles"]]


def validation_playbook(hostname: str) -> list[dict[str, Any]]:
    """The site play reduced to what the argument validation reads.

    The role conditions of site.yml are dropped, so every role is validated
    on every host, including the roles a host does not select: a value set in
    group_vars must stay valid for all of them. The hostname check of
    tasks/target.yml is left out because the tests reach the inventory hosts
    on the local machine.
    """
    play = site_play()
    return [
        {
            "name": "Validate the role arguments",
            "hosts": hostname,
            "become": False,
            "gather_facts": False,
            "vars": play["vars"],
            "pre_tasks": [
                {
                    "name": "Gather the facts the role defaults read",
                    "ansible.builtin.setup": {"gather_subset": ["min", "hardware"]},
                    "tags": ["always"],
                },
                {
                    "name": "Select the package groups of this host",
                    "ansible.builtin.include_role": {
                        "name": "packages",
                        "tasks_from": "selection",
                        "apply": {"tags": ["always"]},
                    },
                    "tags": ["always"],
                },
            ],
            "roles": [{"role": name} for name in site_role_names()],
        }
    ]


class RoleArgumentSpecFileTests(unittest.TestCase):
    """The spec files declare the role defaults, typed and described."""

    def test_site_runs_every_role(self):
        self.assertEqual(sorted(site_role_names()), role_names())

    def test_every_role_has_a_main_spec(self):
        for role in role_names():
            with self.subTest(role=role):
                path = ROLES_DIR / role / "meta/argument_specs.yml"
                self.assertTrue(path.is_file(), f"{path} is missing")
                specs = load_yaml(path)["argument_specs"]
                self.assertIn("main", specs)
                self.assertTrue(specs["main"].get("short_description"))

    def test_options_match_the_role_defaults(self):
        for role in role_names():
            with self.subTest(role=role):
                defaults_file = ROLES_DIR / role / "defaults/main.yml"
                defaults = load_yaml(defaults_file) or {}
                spec = load_yaml(ROLES_DIR / role / "meta/argument_specs.yml")
                options = spec["argument_specs"]["main"].get("options") or {}
                self.assertEqual(sorted(options), sorted(defaults))

    def test_options_are_typed_and_described(self):
        def check(options: dict[str, Any], path: str) -> None:
            for name, option in options.items():
                where = f"{path}.{name}"
                self.assertIn("type", option, where)
                if option["type"] == "list":
                    self.assertIn("elements", option, where)
                self.assertTrue(option.get("description"), where)
                # The defaults live in defaults/main.yml only.
                self.assertNotIn("default", option, where)
                check(option.get("options") or {}, where)

        for role in role_names():
            with self.subTest(role=role):
                spec = load_yaml(ROLES_DIR / role / "meta/argument_specs.yml")
                check(spec["argument_specs"]["main"].get("options") or {}, role)


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
class RoleArgumentValidationTests(unittest.TestCase):
    """Ansible accepts the host configurations and refuses invalid values."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)

    def validate(self, hostname: str, *extra_vars: dict[str, Any]):
        arguments = [*inventory_arguments(hostname, self.work)]
        # Next to site.yml in the test copy of ansible/, so the roles resolve.
        playbook = ansible_tree(self.work) / f"validate-{hostname}.yml"
        playbook.write_text(yaml.safe_dump(validation_playbook(hostname)))
        for variables in extra_vars:
            arguments += ["-e", json.dumps(variables)]
        return run_playbook(
            playbook,
            *arguments,
            "--tags",
            NO_ROLE_TAG,
            env=ansible_test_environment(self.work),
            inventory=None,
            cwd=self.work,
        )

    def test_host_configurations_are_valid(self):
        for hostname in configured_hostnames():
            with self.subTest(hostname=hostname):
                result = self.validate(hostname)
                output = result.stdout + result.stderr
                self.assertEqual(result.returncode, 0, output)
                for role in site_role_names():
                    self.assertIn(f"{role} : {VALIDATION_TASK}", output)

    def test_invalid_values_are_refused(self):
        # Each value breaks the rule the role relies on: a closed set the
        # tasks branch on, a boolean, or a list item shape. An unknown gaming
        # action would otherwise fall through to the fail branch unnoticed.
        # packages_action is left out: the selection pre-task of site.yml
        # asserts it before any role validation runs.
        cases = [
            (
                "gaming",
                {"gaming_power_manager_conflict_action": "uninstall"},
                "gaming_power_manager_conflict_action",
            ),
            (
                "cpu_power",
                {"cpu_power_amd_pstate_epp": "turbo"},
                "cpu_power_amd_pstate_epp",
            ),
            ("dns", {"dns_manage": "maybe"}, "dns_manage"),
            ("dns", {"dns_multicast_dns": "on"}, "dns_multicast_dns"),
            (
                "iwlwifi",
                {"iwlwifi_module_options": [{"module": "e1000e", "options": ["x=1"]}]},
                "module",
            ),
            (
                "iwlwifi",
                {"iwlwifi_module_options": [{"module": "iwlwifi", "option": "x=1"}]},
                "option",
            ),
        ]
        hostname = configured_hostnames()[0]
        for role, variables, option in cases:
            with self.subTest(role=role, variables=variables):
                result = self.validate(hostname, variables)
                output = result.stdout + result.stderr
                self.assertNotEqual(result.returncode, 0, output)
                self.assertIn(f"{role} : {VALIDATION_TASK}", output)
                self.assertIn("Validation of arguments failed", output)
                self.assertIn(option, output)


if __name__ == "__main__":
    unittest.main()
