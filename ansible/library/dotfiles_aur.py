#!/usr/bin/python
"""Install missing AUR packages without relying on helper print-format support."""

from __future__ import annotations

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
---
module: dotfiles_aur
short_description: Install missing packages through yay or paru
description:
  - Queries installed versions with pacman and invokes the helper only for missing packages.
  - Reports package changes even if the helper fails.
options:
  name:
    description: Requested package names.
    type: list
    elements: str
    required: true
  executable:
    description: Selected AUR helper.
    type: str
    choices: [yay, paru]
    required: true
author: Dotfiles maintainers
"""


def installed(module: AnsibleModule) -> dict[str, str]:
    rc, output, error = module.run_command(["pacman", "-Q"])
    if rc:
        raise RuntimeError(f"Cannot read installed packages: {error}")
    return dict(line.split(maxsplit=1) for line in output.splitlines())


def main() -> None:
    module = AnsibleModule(
        argument_spec={
            "name": {"type": "list", "elements": "str", "required": True},
            "executable": {"type": "str", "choices": ["yay", "paru"], "required": True},
        },
        supports_check_mode=True,
    )
    try:
        before = installed(module)
    except (RuntimeError, ValueError) as error:
        module.fail_json(msg=str(error), changed=False)
    missing = sorted(set(module.params["name"]) - before.keys())
    if any(name.startswith("-") for name in missing):
        module.fail_json(msg="Package names cannot start with a dash")
    if module.check_mode or not missing:
        module.exit_json(changed=bool(missing), changed_packages=missing)
    rc, output, error = module.run_command(
        [module.params["executable"], "-S", "--needed", "--noconfirm", "--", *missing]
    )
    try:
        after = installed(module)
    except (RuntimeError, ValueError) as inventory_error:
        module.fail_json(
            msg=str(inventory_error), changed=True, stdout=output, stderr=error
        )
    changes = sorted(
        name
        for name in before.keys() | after.keys()
        if before.get(name) != after.get(name)
    )
    result = {
        "changed": bool(changes),
        "changed_packages": changes,
        "stdout": output,
        "stderr": error,
    }
    if rc or set(missing) - after.keys():
        module.fail_json(
            msg="AUR installation failed or requested packages remain absent", **result
        )
    module.exit_json(**result)


if __name__ == "__main__":
    main()
