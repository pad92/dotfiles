"""Resolve a machine's settings the way the playbooks do, through the inventory."""

import json
import subprocess
from pathlib import Path

import yaml
from ansible_test_environment import ansible_test_environment

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "ansible/inventory.yml"
HOST_FILES = sorted((ROOT / "ansible/host_vars").glob("*.yml"))
# Marks a variable that no group_vars or host_vars file sets.
UNSET = "<role default>"
SETTINGS = [
    "packages_host_groups",
    "hardening_ipv6_enabled",
    "dotfiles_hypridle_enabled",
]


def configured_hostnames():
    return [path.stem for path in HOST_FILES]


def inventory_arguments(hostname):
    """Inventory options that reach hostname locally, with its host_vars.

    The repository inventory is used as is, so Ansible loads group_vars and
    host_vars exactly as it does for `make deploy`. A host outside it is added
    by a second inventory source, like a machine without host_vars.
    """
    arguments = ["-i", str(INVENTORY)]
    if hostname not in yaml.safe_load(INVENTORY.read_text())["all"]["hosts"]:
        arguments += ["-i", f"{hostname},"]
    return arguments + ["-e", "ansible_connection=local"]


def resolve_host_settings(hostname, work):
    """Return the host's settings and warnings for an inventory host name."""
    output = Path(work) / f"settings-{hostname}.json"
    report = {name: f"{{{{ {name} | default({UNSET!r}) }}}}" for name in SETTINGS}
    playbook = Path(work) / f"profile-{hostname}.yml"
    playbook.write_text(
        yaml.safe_dump(
            [
                {
                    "hosts": hostname,
                    "gather_facts": False,
                    "tasks": [
                        {
                            "ansible.builtin.copy": {
                                "content": "{{ report | to_json }}",
                                "dest": str(output),
                                "mode": "0600",
                            },
                            "vars": {"report": report},
                        },
                    ],
                }
            ]
        )
    )
    result = subprocess.run(
        ["ansible-playbook", *inventory_arguments(hostname), str(playbook)],
        cwd=work,
        env=ansible_test_environment(Path(work)),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return json.loads(output.read_text()), result.stderr
