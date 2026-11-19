"""Explicit Ansible paths for fixtures, including world-writable CI checkouts.

The tests share their playbook runner, module loader and paths from here.
"""

import fnmatch
import importlib.util
import os
import shutil
import subprocess
import unittest
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
# The local Vault, ignored by Git: see .gitignore.
LOCAL_VAULT_PATTERN = "vault*.yml"
# A play takes seconds on a workstation but minutes on a loaded CI runner (four
# workers on an old CPU, coverage tracing): the limit only catches a hang.
PLAYBOOK_TIMEOUT = int(os.environ.get("TEST_PLAYBOOK_TIMEOUT", "600"))
# The test ansible.cfg replaces the repository one, which sets collections_path.
COLLECTIONS = ROOT / ".ansible/collections"
# Resolved once: some tests run plays with a PATH that only holds fake tools.
ANSIBLE_PLAYBOOK = shutil.which("ansible-playbook") or "ansible-playbook"


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


def load_module(name: str, path: str | Path) -> ModuleType:
    """Import a repository file that is not a package, such as a filter plugin."""
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def local_play(**fields: Any) -> dict[str, Any]:
    """A play on localhost without fact gathering, completed by the fields."""
    return {
        "hosts": "localhost",
        "connection": "local",
        "gather_facts": False,
        **fields,
    }


def write_playbook(path: Path, plays: Sequence[Mapping[str, Any]]) -> Path:
    """Write the plays as a playbook and return its path."""
    path.write_text(yaml.safe_dump([dict(play) for play in plays]))
    return path


def run_playbook(
    playbook: Path,
    *arguments: str,
    env: Mapping[str, str],
    inventory: str | None = "localhost,",
    cwd: Path = ROOT,
) -> subprocess.CompletedProcess[str]:
    """Run ansible-playbook and capture its output; the caller checks the result.

    inventory=None leaves the inventory options to the arguments.
    """
    command = [ANSIBLE_PLAYBOOK]
    if inventory is not None:
        command += ["-i", inventory]
    return subprocess.run(
        [*command, str(playbook), *arguments],
        cwd=cwd,
        env=dict(env),
        capture_output=True,
        text=True,
        timeout=PLAYBOOK_TIMEOUT,
        check=False,
    )


def play_output(
    test: unittest.TestCase,
    result: subprocess.CompletedProcess[str],
    succeed: bool = True,
) -> str:
    """Assert that the play succeeded or failed as expected; return its output."""
    output = result.stdout + result.stderr
    test.assertEqual(result.returncode == 0, succeed, output)
    return output
