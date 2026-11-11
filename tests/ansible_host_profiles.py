"""Resolve a machine's settings the way the playbooks do, through group_by."""

import json
import subprocess
from pathlib import Path

import yaml
from ansible_test_environment import ansible_test_environment

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "ansible/inventory.yml"
HOST_PROFILE = ROOT / "ansible/tasks/host_profile.yml"
HOST_FILES = sorted((ROOT / "ansible/group_vars").glob("host_*.yml"))
# Marks a variable that no group_vars file sets, so the role default applies.
UNSET = "<role default>"
SETTINGS = [
    "packages_host_groups",
    "hardening_ipv6_enabled",
    "dotfiles_hypridle_enabled",
]


def configured_hostnames():
    return [path.stem.removeprefix("host_") for path in HOST_FILES]


def resolve_host_settings(hostname, work):
    """Return the host's group names, settings and warnings for a hostname fact.

    The play uses the repository inventory, so Ansible loads ansible/group_vars
    exactly as it does for `make install`. The hostname fact is a play variable.
    """
    output = Path(work) / f"settings-{hostname}.json"
    report = {name: f"{{{{ {name} | default({UNSET!r}) }}}}" for name in SETTINGS}
    report["group_names"] = "{{ group_names }}"
    playbook = Path(work) / f"profile-{hostname}.yml"
    playbook.write_text(
        yaml.safe_dump(
            [
                {
                    "hosts": "localhost",
                    "gather_facts": False,
                    "vars": {"ansible_facts": {"hostname": hostname}},
                    "tasks": [
                        {"ansible.builtin.import_tasks": str(HOST_PROFILE)},
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
        ["ansible-playbook", "-i", str(INVENTORY), str(playbook)],
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
