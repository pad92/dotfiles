#!/usr/bin/python
"""Install missing AUR packages without relying on helper print-format support."""

from __future__ import annotations

import os
import shlex
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
---
module: dotfiles_aur
short_description: Install missing packages through yay or paru
description:
  - Asks pacman -T which requested names are unsatisfied, so a package that
    provides a requested name (for example foo-git for foo) counts as installed.
  - Invokes the helper only for unsatisfied packages.
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
  sudo_password:
    description:
      - Password for the sudo calls the helper makes to install built packages.
      - The helper runs as the user and has no terminal under Ansible, so its
        own sudo cannot prompt. When set, the module hands the password to
        sudo through a temporary askpass program removed after the run.
    type: str
    required: false
author: Dotfiles maintainers
"""


def installed(module: AnsibleModule) -> dict[str, str]:
    rc, output, error = module.run_command(["pacman", "-Q"])
    if rc:
        raise RuntimeError(f"Cannot read installed packages: {error}")
    return dict(line.split(maxsplit=1) for line in output.splitlines())


def unsatisfied(module: AnsibleModule, names: list[str]) -> list[str]:
    """Return requested names that no installed package satisfies."""
    if not names:
        return []
    rc, output, error = module.run_command(["pacman", "-T", "--", *names])
    # pacman -T exits 127 when it prints unsatisfied dependencies.
    if rc not in (0, 127):
        raise RuntimeError(f"Cannot check package dependencies: {error}")
    return sorted(set(output.split()))


@contextmanager
def sudo_askpass(password: str | None) -> Iterator[tuple[list[str], dict[str, str]]]:
    """Yield helper arguments and environment that let its sudo read password."""
    if password is None:
        yield [], {}
        return
    with tempfile.TemporaryDirectory(prefix="dotfiles-aur-") as directory:
        secret = os.path.join(directory, "password")
        askpass = os.path.join(directory, "askpass")
        descriptor = os.open(secret, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(password + "\n")
        descriptor = os.open(askpass, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(f"#!/bin/sh\nexec cat -- {shlex.quote(secret)}\n")
        yield ["--sudoflags", "-A"], {"SUDO_ASKPASS": askpass}


def main() -> None:
    module = AnsibleModule(
        argument_spec={
            "name": {"type": "list", "elements": "str", "required": True},
            "executable": {"type": "str", "choices": ["yay", "paru"], "required": True},
            "sudo_password": {"type": "str", "required": False, "no_log": True},
        },
        supports_check_mode=True,
    )
    names = sorted(set(module.params["name"]))
    if any(name.startswith("-") for name in names):
        module.fail_json(msg="Package names cannot start with a dash")
    try:
        before = installed(module)
        missing = unsatisfied(module, names)
    except (RuntimeError, ValueError) as error:
        module.fail_json(msg=str(error), changed=False)
    if module.check_mode or not missing:
        module.exit_json(changed=bool(missing), changed_packages=missing)
    with sudo_askpass(module.params.get("sudo_password")) as (sudo_args, environ):
        rc, output, error = module.run_command(
            [
                module.params["executable"],
                *sudo_args,
                "-S",
                "--needed",
                "--noconfirm",
                "--",
                *missing,
            ],
            environ_update=environ,
        )
    try:
        after = installed(module)
        remaining = unsatisfied(module, missing)
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
    if rc or remaining:
        module.fail_json(
            msg="AUR installation failed or requested packages remain absent", **result
        )
    module.exit_json(**result)


if __name__ == "__main__":
    main()
