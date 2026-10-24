#!/usr/bin/python
"""Build a local Arch package and report generated files."""

from __future__ import annotations

import os
import subprocess

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
---
module: dotfiles_makepkg
short_description: Build a local Arch package and report generated files
description:
  - Runs makepkg without privilege escalation in the supplied build directory.
  - Reports new or modified files and supports check mode.
options:
  path:
    description: Directory containing the package recipe.
    required: true
    type: path
author: Dotfiles maintainers
"""


def main() -> None:
    module = AnsibleModule(
        argument_spec={"path": {"type": "path", "required": True}},
        supports_check_mode=True,
    )
    # Defer custom utilities until after argument discovery by ansible-lint.
    from ansible.module_utils.dotfiles_files import changed_paths, snapshot

    root = os.path.realpath(module.params["path"])
    roots = [root]
    environment = dict(os.environ)
    environment.update(
        {
            name: root
            for name in ("PKGDEST", "SRCDEST", "SRCPKGDEST", "LOGDEST", "BUILDDIR")
        }
    )
    if module.check_mode:
        module.exit_json(changed=True, changed_files=[])
    try:
        before = snapshot(roots)
    except OSError as error:
        module.fail_json(
            msg=f"Cannot inventory output paths before execution: {error}",
            changed=False,
        )
    try:
        result = subprocess.run(
            ["makepkg", "--noconfirm"],
            cwd=root,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        try:
            after = snapshot(roots)
            paths = changed_paths(before, after)
        except OSError as inventory_error:
            module.fail_json(
                msg=f"Execution failed: {error}; inventory failed: {inventory_error}",
                changed=True,
                report_complete=False,
                report_roots=roots,
            )
        module.fail_json(
            msg=f"makepkg failed: {error}", changed=bool(paths), changed_files=paths
        )
    try:
        after = snapshot(roots)
    except OSError as error:
        module.fail_json(
            msg=f"Execution completed but output inventory failed: {error}",
            changed=True,
            report_complete=False,
            report_roots=roots,
        )
    paths = changed_paths(before, after)
    module.exit_json(changed=bool(paths), changed_files=paths, stdout=result.stdout)


if __name__ == "__main__":
    main()
