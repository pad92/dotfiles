"""Remove what earlier versions of this repository left behind.

These leftovers are removed:

- the backups the dotfiles role made next to the paths it manages
  (<path>.bak after a conflict, <path>.<pid>.<date>@<time>~ from a copy),
  found by ansible_backup_files.py. They hold the previous content of a
  file, so they go only after REMOVE is typed on a terminal;
- broken symbolic links under the paths the dotfiles role deploys in the
  home directory, such as a link into a deleted ~/.dotfiles clone or a
  .wants link to a user unit that no longer exists;
- in the repository, the Git metadata of the retired submodules (Vundle,
  tpm, dotbot, the Zsh plugins): their submodule.<name> sections in
  .git/config and their clones under .git/modules, plus the records of
  worktrees whose directory is gone (git worktree prune);
- in the repository, Python tool caches and untracked broken links.

The other leftovers are regenerated or hold no content of their own. A
submodule clone is removed only when every commit its refs reach is also
reachable from a remote-tracking branch or a tag, and when no checkout of it
remains. Otherwise it is kept and reported. Everything is listed before
anything changes, and --dry-run only lists.
"""

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import ansible_backup_files as managed

REPOSITORY_ROOT = managed.REPOSITORY_ROOT
# Directories of the repository that hold other checkouts or installed
# collections; clean never looks into them.
REPOSITORY_SKIPPED_DIRECTORIES = frozenset(
    {".git", ".claude", ".ansible", "node_modules"}
)
CACHE_DIRECTORY_NAMES = frozenset(
    {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
)


@dataclass
class Plan:
    """What clean removes, and what it keeps with the reason."""

    paths: list[Path] = field(default_factory=list)
    backups: list[Path] = field(default_factory=list)
    submodule_sections: list[str] = field(default_factory=list)
    submodule_directories: list[Path] = field(default_factory=list)
    prunable_worktrees: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (
            self.paths
            or self.backups
            or self.submodule_sections
            or self.submodule_directories
            or self.prunable_worktrees
        )


def run_git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def is_broken_link(path: Path) -> bool:
    return path.is_symlink() and not path.exists()


def broken_links_under(directory: Path) -> list[Path]:
    """Broken links in directory and below, without following any link."""
    links = []
    for parent, child_directories, child_files in os.walk(directory):
        for name in child_directories + child_files:
            path = Path(parent) / name
            if is_broken_link(path):
                links.append(path)
    return links


def home_broken_links(root: Path, configuration: dict) -> list[Path]:
    """Broken links at or under the paths the dotfiles role deploys."""
    root = root.resolve(strict=True)
    directories, files = managed.managed_paths(configuration)
    links = set()
    for relative_path in directories:
        directory = root / relative_path
        if managed.has_symlink_component(directory.parent):
            continue
        if is_broken_link(directory):
            links.add(directory)
        elif directory.is_dir() and not directory.is_symlink():
            links.update(broken_links_under(directory))
    for relative_path in files:
        path = root / relative_path
        if not managed.has_symlink_component(path.parent) and is_broken_link(path):
            links.add(path)
    return sorted(links)


def git_common_directory(repository: Path) -> Path:
    result = run_git(
        "rev-parse", "--path-format=absolute", "--git-common-dir", cwd=repository
    )
    if result.returncode != 0:
        raise RuntimeError(f"{repository} is not a Git repository")
    return Path(result.stdout.strip())


def is_main_worktree(repository: Path) -> bool:
    result = run_git(
        "rev-parse",
        "--path-format=absolute",
        "--git-dir",
        "--git-common-dir",
        cwd=repository,
    )
    if result.returncode != 0:
        return False
    git_directory, common_directory = result.stdout.split()
    return git_directory == common_directory


def configured_submodules(common_directory: Path) -> list[str]:
    """Names of the submodule.<name> sections of the repository config."""
    result = run_git(
        "config",
        "--file",
        str(common_directory / "config"),
        "--name-only",
        "--get-regexp",
        r"^submodule\..*\.url$",
    )
    # Exit status 1: no such key, so no submodule section.
    if result.returncode not in (0, 1):
        raise RuntimeError("Unable to read the submodules of the Git config")
    return sorted(
        line[len("submodule.") : -len(".url")]
        for line in result.stdout.splitlines()
        if line
    )


def declared_submodules(repository: Path) -> set[str]:
    """Names the checkout still declares in .gitmodules."""
    gitmodules = repository / ".gitmodules"
    if not gitmodules.is_file():
        return set()
    result = run_git(
        "config",
        "--file",
        str(gitmodules),
        "--name-only",
        "--get-regexp",
        r"^submodule\..*\.path$",
    )
    if result.returncode not in (0, 1):
        raise RuntimeError("Unable to read .gitmodules")
    return {
        line[len("submodule.") : -len(".path")]
        for line in result.stdout.splitlines()
        if line
    }


def nested_git_directories(directory: Path) -> list[Path]:
    """Git directories at or under directory (a submodule's own submodules)."""
    found = []
    for parent, child_directories, _ in os.walk(directory):
        path = Path(parent)
        if (path / "HEAD").is_file() and (path / "objects").is_dir():
            found.append(path)
    return found


def reason_to_keep_clone(git_directory: Path) -> str | None:
    """Why a retired submodule clone holds something found nowhere else."""
    for nested in nested_git_directories(git_directory):
        worktree = run_git("--git-dir", str(nested), "config", "core.worktree")
        if worktree.returncode == 0:
            checkout = (nested / worktree.stdout.strip()).resolve()
            if checkout.is_dir() and any(checkout.iterdir()):
                return f"its checkout {checkout} still exists"
        # Every ref, stash included, must lead only to commits that a
        # remote-tracking branch or a tag also reaches.
        unique = run_git(
            "--git-dir",
            str(nested),
            "--bare",
            "rev-list",
            "--all",
            "--not",
            "--remotes",
            "--tags",
            "-n",
            "1",
        )
        if unique.returncode != 0:
            return f"Git cannot read {nested}"
        if unique.stdout.strip():
            return f"{nested} has commits that no remote branch or tag holds"
    return None


def submodule_leftovers(repository: Path, plan: Plan) -> None:
    if not is_main_worktree(repository):
        plan.kept.append(
            "retired submodules: run clean from the main worktree to remove them"
        )
        return
    common_directory = git_common_directory(repository)
    modules_root = (common_directory / "modules").resolve()
    declared = declared_submodules(repository)
    for name in configured_submodules(common_directory):
        if name in declared:
            continue
        git_directory = (modules_root / name).resolve()
        if not git_directory.is_relative_to(modules_root):
            plan.kept.append(f"submodule {name}: its name leaves .git/modules")
            continue
        if git_directory.is_dir():
            reason = reason_to_keep_clone(git_directory)
            if reason:
                plan.kept.append(f"submodule {name}: {reason}")
                continue
            plan.submodule_directories.append(git_directory)
        plan.submodule_sections.append(name)


def prunable_worktrees(repository: Path) -> list[str]:
    result = run_git("worktree", "prune", "--dry-run", "--verbose", cwd=repository)
    if result.returncode != 0:
        raise RuntimeError("Unable to list the prunable worktrees")
    # Git writes the "Removing worktrees/..." lines to standard error.
    return [line for line in (result.stdout + result.stderr).splitlines() if line]


def is_tracked(repository: Path, path: Path) -> bool:
    result = run_git(
        "ls-files",
        "--error-unmatch",
        "--",
        str(path.relative_to(repository)),
        cwd=repository,
    )
    return result.returncode == 0


def repository_files(repository: Path, plan: Plan) -> None:
    """Python caches and untracked broken links of the working tree."""
    for parent, child_directories, child_files in os.walk(repository):
        parent_path = Path(parent)
        for name in list(child_directories):
            path = parent_path / name
            if name in REPOSITORY_SKIPPED_DIRECTORIES:
                child_directories.remove(name)
            elif name in CACHE_DIRECTORY_NAMES and not path.is_symlink():
                child_directories.remove(name)
                plan.paths.append(path)
        for name in child_directories + child_files:
            path = parent_path / name
            if not is_broken_link(path):
                continue
            if is_tracked(repository, path):
                plan.kept.append(f"{path}: broken link tracked by Git")
            else:
                plan.paths.append(path)


def build_plan(root: Path, configuration: dict, repository: Path) -> Plan:
    plan = Plan()
    plan.backups.extend(managed.find_backups(root, configuration))
    plan.paths.extend(home_broken_links(root, configuration))
    submodule_leftovers(repository, plan)
    plan.prunable_worktrees.extend(prunable_worktrees(repository))
    repository_files(repository, plan)
    return plan


def remove_empty_parents(path: Path, stop: Path) -> None:
    parent = path.parent
    while parent != stop and parent.is_relative_to(stop):
        try:
            parent.rmdir()
        except OSError:
            return
        parent = parent.parent


def remove_path(path: Path) -> None:
    """Remove a file, a link (never what it points to) or a directory tree."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def apply(plan: Plan, repository: Path) -> None:
    for path in plan.backups:
        remove_path(path)
    for path in plan.paths:
        if path.is_symlink():
            if not path.exists():
                path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
    common_directory = (
        git_common_directory(repository)
        if (plan.submodule_sections or plan.submodule_directories)
        else None
    )
    for directory in plan.submodule_directories:
        shutil.rmtree(directory)
        remove_empty_parents(directory, common_directory)
    for name in plan.submodule_sections:
        result = run_git(
            "config",
            "--file",
            str(common_directory / "config"),
            "--remove-section",
            f"submodule.{name}",
        )
        if result.returncode != 0:
            raise RuntimeError(f"Unable to remove submodule.{name} from the Git config")
    if plan.prunable_worktrees:
        result = run_git("worktree", "prune", cwd=repository)
        if result.returncode != 0:
            raise RuntimeError("git worktree prune failed")


def report(plan: Plan, dry_run: bool) -> None:
    verb = "would remove" if dry_run else "remove"
    for path in plan.backups:
        print(f"{verb} backup {path}")
    for path in plan.paths:
        print(f"{verb} {path}")
    for directory in plan.submodule_directories:
        print(f"{verb} {directory}")
    for name in plan.submodule_sections:
        print(f'{verb} [submodule "{name}"] from the Git config')
    for line in plan.prunable_worktrees:
        print(f"{verb} worktree record: {line}")
    for reason in plan.kept:
        print(f"keep {reason}")
    if plan.is_empty():
        print("Nothing to clean.")


def confirm_backup_removal(
    plan: Plan, prompt=input, interactive: bool | None = None
) -> None:
    """Keep the backups unless REMOVE is typed on a terminal."""
    if not plan.backups:
        return
    if interactive is None:
        interactive = sys.stdin.isatty()
    if not interactive:
        reason = "no terminal to confirm their removal"
    else:
        try:
            answer = prompt(
                f"Type REMOVE to delete the {len(plan.backups)} backups listed above: "
            )
        except EOFError:
            answer = ""
        if answer.strip() == "REMOVE":
            return
        reason = "removal not confirmed"
    plan.kept.append(f"{len(plan.backups)} backups: {reason}")
    print(f"keep {plan.kept[-1]}")
    plan.backups.clear()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--root",
        type=Path,
        required=True,
        help="home directory the dotfiles were deployed to",
    )
    parser.add_argument("--repository", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list what would be removed and change nothing",
    )
    parser.add_argument(
        "-e",
        "--extra-vars",
        action="append",
        default=[],
        help="Ansible variable overrides used during deployment (repeatable)",
    )
    arguments = parser.parse_args()

    root = arguments.root.expanduser()
    if not root.is_dir():
        parser.error(f"home is not a directory: {root}")
    repository = arguments.repository.resolve()

    try:
        configuration = managed.load_configuration(root, arguments.extra_vars)
        plan = build_plan(root, configuration, repository)
        report(plan, arguments.dry_run)
        if not arguments.dry_run:
            confirm_backup_removal(plan)
            apply(plan, repository)
    except (
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
        subprocess.TimeoutExpired,
    ) as error:
        print(f"clean stopped: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
