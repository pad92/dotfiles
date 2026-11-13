"""Explicit Ansible paths for fixtures, including world-writable CI checkouts."""

import fnmatch
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The local Vault, ignored by Git: see .gitignore.
LOCAL_VAULT_PATTERN = "vault*.yml"


def ansible_tree(work: Path, source: Path = ROOT / "ansible") -> Path:
    """ansible/ as CI checks it out, without the local Vault.

    group_vars/all/vault.yml is ignored by Git and, on a workstation, encrypted
    with a password the tests do not have: Ansible stops on it before the first
    task of any play that loads group_vars. The playbooks, the inventory and
    the vars files are copied, because Ansible resolves them to their real path
    to find group_vars and host_vars; the other directories are linked.
    """
    tree = work / "ansible"
    if tree.is_dir():
        return tree
    tree.mkdir(parents=True)

    def local_vault(_directory: str, names: list[str]) -> list[str]:
        return fnmatch.filter(names, LOCAL_VAULT_PATTERN)

    for entry in source.iterdir():
        target = tree / entry.name
        if entry.name in ("group_vars", "host_vars"):
            shutil.copytree(entry, target, ignore=local_vault)
        elif entry.is_dir():
            target.symlink_to(entry)
        else:
            shutil.copy2(entry, target)
    return tree


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
