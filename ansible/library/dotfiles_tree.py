#!/usr/bin/python
"""Collect a copy plan, following source links without recursing through cycles."""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
---
module: dotfiles_tree
short_description: Collect a directory copy plan without symlink cycles
description:
  - Read-only traversal including hidden entries and empty directories.
  - Follows readable source links as recursive copy does, preserving dangling and cyclic links.
  - Native find with follow enabled cannot bound symlink cycles.
options:
  path:
    description: Source directory.
    type: path
    required: true
  tracked:
    description:
      - Keep only the files Git tracks under I(path) and the directories
        that lead to them.
      - Ignored and untracked files, such as the plugins and backups a
        program writes into the tree, are left out.
      - A submodule under I(path) fails the task: its files would not be
        copied. Clone such a repository on the target instead.
    type: bool
    default: false
  dest:
    description:
      - Directory the tree is copied to. Each entry then has a C(dest)
        field, the normalized path of its copy under I(dest).
      - Not expanded on the controller, since it names a path on the target.
    type: str
author: Dotfiles maintainers
"""


def git_lines(root: str, *arguments: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", root, *arguments, "-z"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.split("\0") if line]


def tracked_paths(root: str) -> set[str]:
    """Paths relative to root that Git tracks, with the directories above them."""
    paths: set[str] = set()
    for entry in git_lines(root, "ls-files", "--stage"):
        metadata, path = entry.split("\t", 1)
        if metadata.split()[0] == "160000":
            raise OSError(
                f"Submodule in a copied tree: {os.path.join(root, path)}; "
                "clone it on the target instead"
            )
        parts = path.split("/")
        paths.update("/".join(parts[:index]) for index in range(1, len(parts) + 1))
    return paths


def sha1(path: str) -> str:
    # The stat module's default checksum, which the manifest is compared with.
    digest = hashlib.sha1(usedforsecurity=False)
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()


def collect(root: str, tracked: bool = False, dest: str | None = None) -> list[dict]:
    result: list[dict] = []
    if not os.path.isdir(root):
        raise NotADirectoryError(root)
    try:
        selected = tracked_paths(root) if tracked else None
    except subprocess.CalledProcessError as error:
        raise OSError(
            f"cannot list Git-tracked files of {root}: {error.stderr}"
        ) from error

    def visit(path: str, ancestors: set[tuple[int, int]]) -> None:
        relative = os.path.relpath(path, root)
        if selected is not None and relative != "." and relative not in selected:
            return
        info = os.lstat(path)
        link = stat.S_ISLNK(info.st_mode)
        if link:
            try:
                info = os.stat(path)
            except FileNotFoundError:
                pass
        identity = (info.st_dev, info.st_ino)
        preserve_link = link and (stat.S_ISLNK(info.st_mode) or identity in ancestors)
        directory = stat.S_ISDIR(info.st_mode) and not preserve_link
        regular = stat.S_ISREG(info.st_mode) and not preserve_link
        if not (directory or regular or preserve_link):
            raise OSError(f"Unsupported source file type: {path}")
        entry = {
            "path": path,
            "mode": format(stat.S_IMODE(info.st_mode), "04o"),
            "isdir": directory,
            "isreg": regular,
            "islnk": preserve_link,
        }
        if dest is not None:
            entry["dest"] = os.path.normpath(os.path.join(dest, relative))
        if preserve_link:
            entry["lnk_target"] = os.readlink(path)
        if regular:
            entry["checksum"] = sha1(path)
        result.append(entry)
        if directory:
            with os.scandir(path) as children:
                for child in sorted(children, key=lambda entry: entry.name):
                    visit(child.path, ancestors | {identity})

    visit(root, set())
    return result


def main() -> None:
    module = AnsibleModule(
        argument_spec={
            "path": {"type": "path", "required": True},
            "tracked": {"type": "bool", "default": False},
            "dest": {"type": "str"},
        },
        supports_check_mode=True,
    )
    try:
        entries = collect(
            module.params["path"], module.params["tracked"], module.params["dest"]
        )
    except OSError as error:
        module.fail_json(msg=str(error), changed=False)
    module.exit_json(changed=False, files=entries)


if __name__ == "__main__":
    main()
