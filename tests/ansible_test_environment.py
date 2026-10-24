"""Explicit Ansible paths for fixtures, including world-writable CI checkouts."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def ansible_test_environment(work: Path) -> dict[str, str]:
    config = work / "ansible.cfg"
    config.write_text("[defaults]\ninterpreter_python = auto_silent\n")
    return {
        **os.environ,
        "ANSIBLE_CONFIG": str(config),
        "ANSIBLE_LIBRARY": str(ROOT / "ansible/library"),
        "ANSIBLE_MODULE_UTILS": str(ROOT / "ansible/module_utils"),
        "ANSIBLE_FILTER_PLUGINS": str(ROOT / "ansible/filter_plugins"),
        "ANSIBLE_LOCAL_TEMP": str(work / "ansible-local"),
        "ANSIBLE_REMOTE_TEMP": str(work / "ansible-remote"),
    }
