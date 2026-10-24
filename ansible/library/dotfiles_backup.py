#!/usr/bin/python
"""Move a conflict to its backup atomically, preserving the complete inode tree."""

from __future__ import annotations

import ctypes
import errno
import os

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
---
module: dotfiles_backup
short_description: Move a conflicting path without overwriting a backup
description:
  - Uses Linux renameat2 with RENAME_NOREPLACE on the same filesystem.
  - Preserves ownership, modes, links, extended attributes and directory contents.
  - Returns every source and destination path, including in check mode.
options:
  src:
    description: Existing conflict path.
    type: path
    required: true
  dest:
    description: Backup path which must not exist.
    type: path
    required: true
author: Dotfiles maintainers
"""


def tree_paths(path: str) -> list[str]:
    paths = [path]
    if os.path.isdir(path) and not os.path.islink(path):
        with os.scandir(path) as entries:
            for entry in entries:
                paths.extend(tree_paths(entry.path))
    return sorted(paths)


def move_without_replace(src: str, dest: str) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, "renameat2", None)
    if rename is None:
        raise OSError(errno.ENOSYS, "renameat2 is required; source left untouched")
    rename.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    rename.restype = ctypes.c_int
    if rename(-100, os.fsencode(src), -100, os.fsencode(dest), 1):
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), dest)


def main() -> None:
    module = AnsibleModule(
        argument_spec={
            "src": {"type": "path", "required": True},
            "dest": {"type": "path", "required": True},
        },
        supports_check_mode=True,
    )
    src, dest = module.params["src"], module.params["dest"]
    try:
        if os.path.lexists(dest):
            raise FileExistsError(f"Backup already exists: {dest}")
        paths = tree_paths(src)
        if not os.path.lexists(src):
            raise FileNotFoundError(src)
        changed_files = paths + [dest + path[len(src) :] for path in paths]
        if not module.check_mode:
            move_without_replace(src, dest)
    except OSError as error:
        module.fail_json(msg=str(error), changed=False)
    module.exit_json(changed=True, changed_files=changed_files, src=src, dest=dest)


if __name__ == "__main__":
    main()
