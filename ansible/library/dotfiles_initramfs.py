#!/usr/bin/python
"""Regenerate initramfs images and report files whose contents changed."""

from __future__ import annotations

import subprocess

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
---
module: dotfiles_initramfs
short_description: Regenerate initramfs images and report changed files
description:
  - Runs the selected initramfs generator.
  - Reports changed files below /boot and /efi and supports check mode.
options:
  generator:
    description: Installed initramfs generator to run.
    required: true
    choices: [mkinitcpio, dracut]
    type: str
  report_roots:
    description: Complete list of output trees configured for the generator and its hooks.
    type: list
    elements: path
    default: [/boot, /efi]
author: Dotfiles maintainers
"""


def main() -> None:
    module = AnsibleModule(
        argument_spec={
            "report_roots": {
                "type": "list",
                "elements": "path",
                "default": ["/boot", "/efi"],
            },
            "generator": {
                "type": "str",
                "choices": ["mkinitcpio", "dracut"],
                "required": True,
            },
        },
        supports_check_mode=True,
    )
    # Defer custom utilities until after argument discovery by ansible-lint.
    from ansible.module_utils.dotfiles_files import changed_paths, snapshot

    generator = module.params["generator"]
    command = (
        ["mkinitcpio", "-P"]
        if generator == "mkinitcpio"
        else ["dracut", "--regenerate-all", "--force"]
    )
    roots = module.params["report_roots"]
    if module.check_mode:
        module.exit_json(changed=True, changed_files=[], planned_command=command)
    try:
        before = snapshot(roots)
    except OSError as error:
        module.fail_json(
            msg=f"Cannot inventory output paths before execution: {error}",
            changed=False,
        )
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
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
            msg=f"{generator} failed: {error}", changed=bool(paths), changed_files=paths
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
    module.exit_json(
        changed=bool(paths),
        changed_files=paths,
        stdout=result.stdout,
        stderr=result.stderr,
    )


if __name__ == "__main__":
    main()
