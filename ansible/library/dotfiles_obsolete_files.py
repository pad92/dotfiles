#!/usr/bin/python
"""Delete files a role no longer ships, but only while they hold what it shipped."""

from __future__ import annotations

import hashlib
import os
import stat

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
---
module: dotfiles_obsolete_files
short_description: Delete obsolete files that still hold their shipped content
description:
  - Each path is deleted only when it is a regular file whose SHA-1 equals the
    checksum it was shipped with.
  - A missing path is ignored. A changed file, a link or any other non-regular
    file is kept and listed in C(kept) with the reason.
  - Check mode reports the deletions without deleting.
options:
  files:
    description: Absolute path of each obsolete file, mapped to its shipped SHA-1.
    type: dict
    required: true
author: Dotfiles maintainers
"""

RETURN = r"""
deleted:
  description: Paths deleted, or that would be deleted in check mode.
  type: list
  elements: str
kept:
  description: Paths kept, each with the reason.
  type: list
  elements: dict
"""

CHANGED = "was changed by hand"
NOT_REGULAR = "is not a regular file"


def sha1(path: str) -> str:
    digest = hashlib.sha1(usedforsecurity=False)
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()


def classify(path: str, checksum: str) -> str | None:
    """Return None to delete the path, or the reason to keep it."""
    mode = os.lstat(path).st_mode
    if not stat.S_ISREG(mode):
        return NOT_REGULAR
    if sha1(path) != checksum.lower():
        return CHANGED
    return None


def main() -> None:
    module = AnsibleModule(
        argument_spec={"files": {"type": "dict", "required": True}},
        supports_check_mode=True,
    )
    deleted: list[str] = []
    kept: list[dict[str, str]] = []
    for path, checksum in sorted(module.params["files"].items()):
        if not os.path.isabs(path):
            module.fail_json(msg=f"Not an absolute path: {path}", changed=False)
        try:
            if not os.path.lexists(path):
                continue
            reason = classify(path, str(checksum))
            if reason is not None:
                kept.append({"path": path, "reason": reason})
                continue
            if not module.check_mode:
                os.unlink(path)
            deleted.append(path)
        except OSError as error:
            module.fail_json(
                msg=f"Cannot handle {path}: {error}",
                changed=bool(deleted),
                deleted=deleted,
                kept=kept,
            )
    module.exit_json(changed=bool(deleted), deleted=deleted, kept=kept)


if __name__ == "__main__":
    main()
