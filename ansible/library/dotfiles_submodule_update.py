#!/usr/bin/python
"""Initialize recorded submodule revisions and report changed paths."""

from __future__ import annotations

import os
import subprocess

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
---
module: dotfiles_submodule_update
short_description: Initialize recorded Git submodule revisions
description:
  - Updates recursive submodules to the revisions recorded by the parent repository.
  - Returns paths changed by the update.
options:
  path:
    description: Parent Git repository path.
    required: true
    type: path
author: Dotfiles maintainers
"""


def submodule_revisions(
    root: str, expected: bool = False
) -> dict[str, tuple[str, bool]]:
    """Read NUL-delimited index entries; status output includes human descriptions."""
    result = subprocess.run(
        ["git", "-C", root, "ls-files", "--stage", "-z"],
        check=True,
        capture_output=True,
        text=True,
    )
    revisions: dict[str, tuple[str, bool]] = {}
    for entry in result.stdout.split("\0"):
        if not entry:
            continue
        metadata, path = entry.split("\t", 1)
        mode, revision, stage = metadata.split()
        if mode != "160000":
            continue
        if stage != "0":
            raise ValueError(f"Unmerged submodule: {path}")
        directory = os.path.join(root, path)
        initialized = os.path.exists(os.path.join(directory, ".git"))
        if initialized:
            actual = subprocess.run(
                ["git", "-C", directory, "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            revisions[path] = (revision if expected else actual, True)
            for child, value in submodule_revisions(directory, expected).items():
                revisions[f"{path}/{child}"] = value
        else:
            revisions[path] = (revision, False)
    return revisions


def changed_submodule_files(
    root: str,
    before: dict[str, tuple[str, bool]],
    after: dict[str, tuple[str, bool]],
) -> list[str]:
    paths: set[str] = set()
    for submodule in before.keys() | after.keys():
        old_revision, old_initialized = before.get(submodule, ("", False))
        new_revision, new_initialized = after.get(submodule, ("", False))
        if (old_revision, old_initialized) == (new_revision, new_initialized):
            continue
        directory = f"{root}/{submodule}"
        if old_initialized and new_initialized:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    directory,
                    "diff",
                    "--name-only",
                    "--no-renames",
                    "-z",
                    old_revision,
                    new_revision,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            files = [path for path in result.stdout.split("\0") if path]
        elif new_initialized:
            result = subprocess.run(
                ["git", "-C", directory, "ls-files", "-z"],
                check=True,
                capture_output=True,
                text=True,
            )
            files = [path for path in result.stdout.split("\0") if path]
        else:
            files = []
        paths.update(os.path.join(root, submodule, path) for path in files)
        if not files:
            paths.add(directory)
    return sorted(paths)


def main() -> None:
    module = AnsibleModule(
        argument_spec={"path": {"type": "path", "required": True}},
        supports_check_mode=True,
    )
    root = module.params["path"]
    if module.check_mode:
        try:
            actual = submodule_revisions(root)
            expected = submodule_revisions(root, expected=True)
            paths = [
                os.path.join(root, path)
                for path, value in actual.items()
                if not value[1] or value != expected[path]
            ]
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            module.fail_json(msg=f"cannot inspect submodules: {error}")
        module.exit_json(changed=bool(paths), changed_files=sorted(paths))
    try:
        before = submodule_revisions(root)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        module.fail_json(
            msg=f"cannot inspect submodules before update: {error}", changed=False
        )
    try:
        result = subprocess.run(
            ["git", "-C", root, "submodule", "update", "--init", "--recursive"],
            check=True,
            capture_output=True,
            text=True,
        )
        after = submodule_revisions(root)
        paths = changed_submodule_files(root, before, after)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        try:
            after = submodule_revisions(root)
            paths = changed_submodule_files(root, before, after)
        except (OSError, ValueError, subprocess.CalledProcessError) as inventory_error:
            module.fail_json(
                msg=f"submodule update failed: {error}; inventory failed: {inventory_error}",
                changed=True,
                report_complete=False,
                path=root,
            )
        module.fail_json(
            msg=f"submodule update failed: {error}",
            changed=bool(paths),
            changed_files=paths,
        )
    module.exit_json(
        changed=bool(paths),
        changed_files=paths,
        stdout=result.stdout,
        stderr=result.stderr,
    )


if __name__ == "__main__":
    main()
