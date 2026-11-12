#!/usr/bin/python
"""Collect a copy plan, following source links without recursing through cycles."""

from __future__ import annotations

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
      - Keep only what Git tracks under I(path), the files of initialized
        submodules included, and the directories that lead to them.
      - Ignored and untracked files, such as the plugins and backups a
        program writes into the tree, are left out, and so are the C(.git)
        entries of the submodules.
      - Fails when a submodule under I(path) is not initialized, since its
        files would silently be missing.
    type: bool
    default: false
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
    """Paths relative to root that Git tracks, with the directories above them.

    ls-files omits a submodule that is not initialized, so its gitlink is
    looked up in the index to refuse a copy that would lack its files.
    """
    for entry in git_lines(root, "ls-files", "--stage"):
        metadata, path = entry.split("\t", 1)
        if metadata.split()[0] == "160000" and not os.path.exists(
            os.path.join(root, path, ".git")
        ):
            raise OSError(f"Submodule not initialized: {os.path.join(root, path)}")
    paths: set[str] = set()
    for path in git_lines(root, "ls-files", "--recurse-submodules"):
        parts = path.split("/")
        paths.update("/".join(parts[:index]) for index in range(1, len(parts) + 1))
    return paths


def collect(root: str, tracked: bool = False) -> list[dict]:
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
        if preserve_link:
            entry["lnk_target"] = os.readlink(path)
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
        },
        supports_check_mode=True,
    )
    try:
        entries = collect(module.params["path"], module.params["tracked"])
    except OSError as error:
        module.fail_json(msg=str(error), changed=False)
    module.exit_json(changed=False, files=entries)


if __name__ == "__main__":
    main()
