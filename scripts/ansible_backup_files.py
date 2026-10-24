"""List backups created for paths managed by the Ansible roles."""

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

from ansible.errors import AnsibleError
from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar, trust_as_template

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DOTFILES_DEFAULTS = REPOSITORY_ROOT / "ansible/roles/dotfiles/defaults/main.yml"
TIMESTAMP_SUFFIX = re.compile(
    r"^(?P<name>.+?)\.(?:\d+\.)?\d{4}-\d{2}-\d{2}@\d{2}:\d{2}:\d{2}~$"
)
PATH_VARIABLES = (
    "dotfiles_directories",
    "dotfiles_files",
    "dotfiles_templates",
    "dotfiles_links",
    "dotfiles_systemd_directory",
)


def trust_inventory_templates(value: object) -> object:
    """Keep template semantics when reading this project's inventory as JSON."""
    if isinstance(value, str):
        return trust_as_template(value)
    if isinstance(value, list):
        return [trust_inventory_templates(item) for item in value]
    if isinstance(value, dict):
        return {key: trust_inventory_templates(item) for key, item in value.items()}
    return value


def load_configuration(root: Path, extra_vars: list[str]) -> dict:
    """Resolve role defaults and localhost inventory overrides through Ansible."""
    command = [
        "ansible-inventory",
        "--playbook-dir",
        str(REPOSITORY_ROOT / "ansible"),
        "--host",
        "localhost",
    ]
    for variables in extra_vars:
        command.extend(["--extra-vars", variables])
    try:
        result = subprocess.run(
            command,
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "Unable to read the Ansible inventory; check inventory and Vault access."
            )
        inventory = json.loads(result.stdout)
        if not isinstance(inventory, dict):
            raise TypeError("Expected inventory variables")
        loader = DataLoader()
        defaults = loader.load_from_file(
            str(DOTFILES_DEFAULTS), trusted_as_template=True
        )
        variables = {
            **defaults,
            **trust_inventory_templates(inventory),
            "dotfiles_home": str(root),
            "dotfiles_repository": str(REPOSITORY_ROOT),
        }
        templar = Templar(loader=loader, variables=variables)
        return {name: templar.template(variables[name]) for name in PATH_VARIABLES}
    except (
        AnsibleError,
        KeyError,
        TypeError,
        ValueError,
        subprocess.TimeoutExpired,
    ) as error:
        # Inventory values and Ansible exception text can contain Vault secrets.
        raise RuntimeError(
            "Unable to resolve managed paths from the Ansible configuration."
        ) from error


def validate_relative_path(value: object) -> str:
    """Reject unresolved or escaping paths before looking for removable files."""
    if (
        not isinstance(value, str)
        or not value
        or any(marker in value for marker in ("{{", "{%", "{#"))
    ):
        raise ValueError("Managed paths must be fully resolved strings")
    path = Path(value)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError("Managed user paths must stay inside the selected home")
    return path.as_posix()


def has_symlink_component(path: Path) -> bool:
    """Return whether any existing component in an absolute path is a symlink."""
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        if current.is_symlink():
            return True
    return False


def managed_paths(defaults: dict) -> tuple[list[str], list[str]]:
    """Return the exact managed paths whose Ansible tasks can back up."""
    directories = (
        defaults["dotfiles_directories"]
        + [link["dest"] for link in defaults["dotfiles_links"]]
        + [
            defaults["dotfiles_systemd_directory"],
            defaults["dotfiles_systemd_directory"] + "/user",
        ]
    )
    files = set(
        defaults["dotfiles_files"]
        + [template["dest"] for template in defaults["dotfiles_templates"]]
        + [
            ".config/waybar/config",
            ".config/hypr/hyprlock/carousel-image.sh",
        ]
    )

    source_root = REPOSITORY_ROOT / "ansible/roles/dotfiles/files/home"
    source_directories = (
        [
            (relative_path, relative_path)
            for relative_path in defaults["dotfiles_directories"]
        ]
        + [
            (link["src"], link["dest"])
            for link in defaults["dotfiles_links"]
            if (source_root / validate_relative_path(link["src"])).is_dir()
        ]
        + [
            (
                defaults["dotfiles_systemd_directory"],
                defaults["dotfiles_systemd_directory"],
            ),
        ]
    )
    for source_relative, destination_relative in source_directories:
        source_directory = source_root / validate_relative_path(source_relative)
        if not source_directory.is_dir():
            raise RuntimeError(
                "A managed source directory is missing; cannot enumerate backups safely."
            )

        def raise_walk_error(error):
            raise error

        for parent, child_directories, child_files in os.walk(
            source_directory, followlinks=False, onerror=raise_walk_error
        ):
            relative_parent = Path(parent).relative_to(source_directory)
            names = child_directories + child_files
            for name in names:
                relative_path = relative_parent / name
                files.add((Path(destination_relative) / relative_path).as_posix())

    return [validate_relative_path(path) for path in directories], sorted(
        {validate_relative_path(path) for path in files}
    )


def find_backups(root: Path, configuration: dict) -> list[Path]:
    """Find backups only next to paths managed by the dotfiles role."""
    root = root.resolve(strict=True)
    directories, files = managed_paths(configuration)
    all_paths = directories + files
    candidates = set()

    for relative_path in all_paths:
        target = root / relative_path
        backup = target.with_name(target.name + ".bak")
        if not has_symlink_component(target.parent) and (
            backup.exists() or backup.is_symlink()
        ):
            candidates.add(backup)

        candidates.update(timestamp_siblings(target))

    return sorted(
        candidates, key=lambda path: (len(path.parts), str(path)), reverse=True
    )


def timestamp_siblings(target: Path) -> set[Path]:
    """Return timestamp backups whose base path is exactly target."""
    if not target.parent.is_dir() or has_symlink_component(target.parent):
        return set()

    backups = set()
    for sibling in target.parent.iterdir():
        match = TIMESTAMP_SUFFIX.fullmatch(sibling.name)
        if match and match.group("name") == target.name:
            backups.add(sibling)
    return backups


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("list",))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "-e",
        "--extra-vars",
        action="append",
        default=[],
        help="Ansible variable overrides used during deployment (repeatable)",
    )
    arguments = parser.parse_args()

    root = arguments.root.expanduser()
    if not root.is_dir():
        parser.error(f"backup root is not a directory: {root}")

    try:
        configuration = load_configuration(root, arguments.extra_vars)
        backups = find_backups(root, configuration)
    except (OSError, RuntimeError, ValueError, TypeError) as error:
        print(f"Unable to enumerate backups: {error}", file=sys.stderr)
        return 1
    if arguments.json:
        print(json.dumps([str(path) for path in backups]))
        return 0
    if not backups:
        print(f"No Ansible-managed backups found under {root}.")
        return 0

    for backup in backups:
        print(shlex.quote(str(backup)))

    return 0


if __name__ == "__main__":
    sys.exit(main())
