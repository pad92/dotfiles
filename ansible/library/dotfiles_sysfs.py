#!/usr/bin/python
"""Set one sysfs control through an Ansible module and report its path."""

from __future__ import annotations

import os

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
---
module: dotfiles_sysfs
short_description: Set one sysfs control and report its path
description:
  - Writes an idempotent value to a control below /sys.
  - Reports the changed path and supports check mode.
options:
  path:
    description: Sysfs control path.
    required: true
    type: path
  value:
    description: Value to write.
    required: true
    type: str
author: Dotfiles maintainers
"""


def main() -> None:
    module = AnsibleModule(
        argument_spec={
            "path": {"type": "path", "required": True},
            "value": {"type": "str", "required": True},
        },
        supports_check_mode=True,
    )
    path = os.path.realpath(module.params["path"])
    if not path.startswith("/sys/"):
        module.fail_json(msg="path must resolve below /sys")
    value = module.params["value"].strip()
    try:
        with open(path, encoding="utf-8") as control:
            current = control.read().strip()
    except OSError as error:
        module.fail_json(msg=f"cannot read {path}: {error}")
    if current == value:
        module.exit_json(changed=False, path=path, changed_files=[])
    if module.check_mode:
        module.exit_json(changed=True, path=path, changed_files=[path])
    try:
        with open(path, "w", encoding="utf-8") as control:
            control.write(value + "\n")
    except OSError as error:
        module.fail_json(
            msg=f"cannot write {path}: {error}",
            changed=True,
            path=path,
            changed_files=[path],
        )
    try:
        with open(path, encoding="utf-8") as control:
            actual = control.read().strip()
        if actual != value:
            module.fail_json(
                msg=f"{path}: requested {value!r}, read back {actual!r}",
                changed=True,
                path=path,
                changed_files=[path],
            )
    except OSError as error:
        module.fail_json(
            msg=f"cannot verify {path}: {error}",
            changed=True,
            path=path,
            changed_files=[path],
        )
    module.exit_json(changed=True, path=path, changed_files=[path])


if __name__ == "__main__":
    main()
