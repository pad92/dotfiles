#!/usr/bin/python
"""Collect a copy plan, following source links without recursing through cycles."""

from __future__ import annotations

import os
import stat

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
author: Dotfiles maintainers
"""


def collect(root: str) -> list[dict]:
    result: list[dict] = []

    def visit(path: str, ancestors: set[tuple[int, int]]) -> None:
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

    if not os.path.isdir(root):
        raise NotADirectoryError(root)
    visit(root, set())
    return result


def main() -> None:
    module = AnsibleModule(
        argument_spec={"path": {"type": "path", "required": True}},
        supports_check_mode=True,
    )
    try:
        entries = collect(module.params["path"])
    except OSError as error:
        module.fail_json(msg=str(error), changed=False)
    module.exit_json(changed=False, files=entries)


if __name__ == "__main__":
    main()
