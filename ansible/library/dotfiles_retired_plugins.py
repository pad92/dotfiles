#!/usr/bin/python
"""Remove the plugin directories that Vundle and tpm left in a home."""

from __future__ import annotations

import os
import shutil
import subprocess

from ansible.module_utils.basic import AnsibleModule

BACKUP_SUFFIX = ".bak"

DOCUMENTATION = r"""
---
module: dotfiles_retired_plugins
short_description: Remove retired plugin directories, keeping local work
description:
  - Each path in C(paths) is removed with everything under it. A path that
    is a symbolic link loses the link only.
  - A path that holds anything besides Git repositories (a file, a link or
    a special file outside every repository) is not removed but moved, whole,
    to C(<path>.bak); so is a path that is a regular file. Empty directories
    do not count. When a C(.bak) already exists, the module fails, names it,
    and changes nothing, as dotfiles_backup does.
  - Every Git repository found under a path is checked first. When one has
    uncommitted or untracked changes, a stash, or commits that no
    remote-tracking branch holds, the module fails, names it, and removes
    nothing at all.
  - Paths are resolved under C(home) without following links. When a
    directory above a path is a link, the path is left alone, unless that
    directory is listed in C(parents): then the link is removed, and its
    target is neither followed nor changed.
  - A directory of C(parents) that is a real directory is removed once one
    of its paths was removed and it is left empty. If it still holds
    something, it is kept and reported as a warning.
  - In check mode, the result lists what would be removed or backed up.
options:
  home:
    description: Home directory the paths are relative to.
    type: path
    required: true
  paths:
    description: Relative paths to remove.
    type: list
    elements: str
    required: true
  parents:
    description: Relative directories above C(paths) that may go as well.
    type: list
    elements: str
    default: []
author: Dotfiles maintainers
"""


class LocalWork(Exception):
    """A repository holds work that removing it would lose."""


def git(repository: str, *arguments: str) -> subprocess.CompletedProcess:
    # A GIT_DIR or GIT_WORK_TREE inherited from a hook would point Git at
    # another repository than the one under -C.
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    try:
        return subprocess.run(
            ["git", "-C", repository, *arguments],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
    except OSError as error:
        raise LocalWork(f"cannot run git: {error}") from error


def local_work(repository: str) -> list[str]:
    """Describe what in a repository exists nowhere else."""
    found = []
    status = git(
        repository,
        "status",
        "--porcelain",
        "--untracked-files=all",
        "--ignore-submodules=none",
    )
    if status.returncode != 0:
        raise LocalWork(f"cannot read its Git status: {status.stderr.strip()}")
    if status.stdout.strip():
        found.append("uncommitted changes")
    revisions = ["--branches"]
    if git(repository, "rev-parse", "-q", "--verify", "HEAD").returncode == 0:
        revisions.append("HEAD")
    unpushed = git(repository, "rev-list", "-n", "1", *revisions, "--not", "--remotes")
    if unpushed.returncode != 0:
        raise LocalWork(f"cannot list its commits: {unpushed.stderr.strip()}")
    if unpushed.stdout.strip():
        found.append("commits that no remote branch holds")
    if git(repository, "rev-parse", "-q", "--verify", "refs/stash").returncode == 0:
        found.append("a stash")
    return found


def repositories(path: str) -> list[str]:
    """List the Git repositories under a directory, nested ones included."""
    found = []
    for directory, directories, files in os.walk(path, followlinks=False):
        if ".git" in directories or ".git" in files:
            found.append(directory)
            if ".git" in directories:
                directories.remove(".git")
        directories.sort()
    return found


def foreign_entries(path: str) -> list[str]:
    """List what under a directory lies outside every Git repository.

    Directories are walked without following links. A repository is not
    entered: its own content is checked by local_work. Empty directories
    hold nothing to lose and are not listed.
    """
    found = []
    for directory, directories, files in os.walk(path, followlinks=False):
        if ".git" in directories or ".git" in files:
            directories.clear()
            continue
        for name in sorted(directories):
            if os.path.islink(os.path.join(directory, name)):
                found.append(os.path.join(directory, name))
                directories.remove(name)
        found.extend(os.path.join(directory, name) for name in sorted(files))
        directories.sort()
    return found


def plan(home: str, paths: list[str], parents: list[str]) -> dict:
    """Decide what goes, without changing anything."""
    remove, unlink, backup, emptied, skipped = [], [], [], [], []
    for relative in paths:
        parts = os.path.normpath(relative).split(os.sep)
        if relative.startswith("/") or ".." in parts:
            raise ValueError(f"{relative} must stay under the home directory")
        through_link = False
        for depth in range(1, len(parts)):
            prefix = os.path.join(*parts[:depth])
            absolute = os.path.join(home, prefix)
            if not os.path.islink(absolute):
                continue
            through_link = True
            if prefix in parents:
                if absolute not in unlink:
                    unlink.append(absolute)
            else:
                skipped.append(f"{os.path.join(home, relative)}: {absolute} is a link")
            break
        absolute = os.path.join(home, relative)
        if through_link or not os.path.lexists(absolute):
            continue
        if os.path.islink(absolute):
            unlink.append(absolute)
            continue
        if not os.path.isdir(absolute) or foreign_entries(absolute):
            backup.append(absolute)
        else:
            remove.append(absolute)
        for parent in parents:
            if relative.startswith(parent.rstrip("/") + "/"):
                directory = os.path.join(home, parent)
                if directory not in emptied:
                    emptied.append(directory)
    return {
        "remove": remove,
        "unlink": unlink,
        "backup": backup,
        "emptied": emptied,
        "skipped": skipped,
    }


def main() -> None:
    module = AnsibleModule(
        argument_spec={
            "home": {"type": "path", "required": True},
            "paths": {"type": "list", "elements": "str", "required": True},
            "parents": {"type": "list", "elements": "str", "default": []},
        },
        supports_check_mode=True,
    )
    # Defer custom utilities until after argument discovery by ansible-lint.
    from ansible.module_utils.dotfiles_files import move_without_replace

    home = module.params["home"]
    parents = [os.path.normpath(parent) for parent in module.params["parents"]]
    try:
        decided = plan(home, module.params["paths"], parents)
    except ValueError as error:
        module.fail_json(msg=str(error), changed=False)

    blocked = []
    for path in decided["remove"] + decided["backup"]:
        for repository in repositories(path):
            try:
                found = local_work(repository)
            except LocalWork as error:
                found = [str(error)]
            if found:
                blocked.append(f"{repository} ({', '.join(found)})")
    if blocked:
        module.fail_json(
            msg=(
                "Refusing to remove the Vundle and tpm leftovers, since these "
                "repositories hold local work: "
                + "; ".join(blocked)
                + ". Push or save that work, or move the repository away, "
                "then deploy again."
            ),
            blocked=blocked,
            changed=False,
        )
    existing = [
        path + BACKUP_SUFFIX
        for path in decided["backup"]
        if os.path.lexists(path + BACKUP_SUFFIX)
    ]
    if existing:
        module.fail_json(
            msg=(
                "Refusing to back up the Vundle and tpm leftovers, since these "
                "backups already exist: "
                + ", ".join(existing)
                + ". Move or delete them, then deploy again."
            ),
            changed=False,
        )

    removed = decided["unlink"] + decided["remove"]
    kept = []
    for directory in decided["emptied"]:
        with os.scandir(directory) as entries:
            left = sorted(
                (
                    entry.name + BACKUP_SUFFIX
                    if entry.path in decided["backup"]
                    else entry.name
                )
                for entry in entries
                if entry.path not in removed
            )
        if left:
            kept.append(directory)
            module.warn(
                f"Kept {directory}, which still holds {', '.join(left)}; "
                "remove it by hand once it is no longer needed."
            )
        else:
            removed.append(directory)

    if not module.check_mode:
        for path in decided["unlink"]:
            os.unlink(path)
        for path in decided["remove"]:
            shutil.rmtree(path)
        for path in decided["backup"]:
            try:
                move_without_replace(path, path + BACKUP_SUFFIX)
            except OSError as error:
                module.fail_json(msg=f"Cannot back up {path}: {error}", changed=True)
        for directory in decided["emptied"]:
            if directory not in kept:
                os.rmdir(directory)
    module.exit_json(
        changed=bool(removed or decided["backup"]),
        removed=removed,
        backed_up=decided["backup"],
        kept=kept,
        skipped=decided["skipped"],
    )


if __name__ == "__main__":
    main()
