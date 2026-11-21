"""Remove what earlier versions of this repository left behind.

These leftovers are removed:

- the backups the dotfiles role made next to the paths it manages
  (<path>.bak after a conflict, <path>.<pid>.<date>@<time>~ from a copy),
  found by ansible_backup_files.py;
- the timestamp backups of the system files the roles write (/etc/pacman.conf,
  sysctl.d, modprobe.d...), where the user may write; run clean as root for
  the others, which are reported and kept;
- broken symbolic links under the paths the dotfiles role deploys in the
  home directory, such as a link into a deleted ~/.dotfiles clone or a
  .wants link to a user unit that no longer exists;
- in the repository, the Git metadata of the retired submodules (Vundle,
  tpm, dotbot, the Zsh plugins): their submodule.<name> sections in
  .git/config and their clones under .git/modules, plus the records of
  worktrees whose directory is gone (git worktree prune);
- the files a role no longer ships (audio_obsolete_files), while they
  still hold the shipped content: a changed copy or a link is kept and
  reported, like the deployment does;
- in the repository, Python tool caches and untracked broken links, outside
  nested Git checkouts and Python virtual environments;
- the obsolete launchers (.desktop files) of ~/.local/share/applications and
  ~/.config/autostart: their TryExec or program is gone, the command is no
  longer installed, their WINEPREFIX is deleted or their Steam game is
  uninstalled. A path under a filesystem that is not mounted, or that cannot
  be read, is not proof of absence: the launcher is kept.

Backups, launchers, submodule metadata and worktree records go only after REMOVE is
typed on a terminal: a backup holds the previous content of a file, and a
worktree record may name a checkout on a drive that is not mounted. Caches,
broken links and unchanged obsolete files are regenerated or hold no content
of their own, so they go without asking. A submodule clone is removed only when every commit its refs
reach is also reachable from a remote-tracking branch or a tag, and when no
checkout of it remains. Otherwise it is kept and reported. Everything is
listed before anything changes, and --dry-run only lists.
"""

import argparse
import importlib.util
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import ansible_backup_files as managed

REPOSITORY_ROOT = managed.REPOSITORY_ROOT
# The deployment's own rule decides which obsolete files may go.
_OBSOLETE_SPEC = importlib.util.spec_from_file_location(
    "dotfiles_obsolete_files",
    REPOSITORY_ROOT / "ansible/library/dotfiles_obsolete_files.py",
)
obsolete_files_module = importlib.util.module_from_spec(_OBSOLETE_SPEC)
_OBSOLETE_SPEC.loader.exec_module(obsolete_files_module)
# Directories of the repository that hold other checkouts or installed
# collections; clean never looks into them.
REPOSITORY_SKIPPED_DIRECTORIES = frozenset(
    {".git", ".claude", ".ansible", "node_modules"}
)
CACHE_DIRECTORY_NAMES = frozenset(
    {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
)
# Directories of the home whose .desktop launchers clean checks.
LAUNCHER_DIRECTORIES = (".local/share/applications", ".config/autostart")
# Where a desktop session finds commands that a shell PATH may lack.
LAUNCHER_SEARCH_DIRECTORIES = (
    "/usr/local/bin",
    "/usr/bin",
    "/bin",
    "/usr/games",
    "/var/lib/flatpak/exports/bin",
)
HOME_SEARCH_DIRECTORIES = (".local/bin", ".bin", ".local/share/flatpak/exports/bin")
# Removable media appear there only while they are mounted.
REMOVABLE_MEDIA_ROOTS = (Path("/media"), Path("/run/media"))
STEAM_GAME_URL = re.compile(r"^steam://(?:rungameid|run)/(\d+)/?$")
# Larger ids are shortcuts to non-Steam games, without an app manifest.
STEAM_APP_ID_LIMIT = 2**32
STEAM_LIBRARY_PATH = re.compile(r'^\s*"path"\s+"((?:[^"\\]|\\.)*)"', re.MULTILINE)
# Native and Flatpak Steam installs, relative to the home.
STEAM_DIRECTORIES = (
    ".local/share/Steam",
    ".steam/steam",
    ".var/app/com.valvesoftware.Steam/.local/share/Steam",
)
# String escapes of desktop entry values, decoded before Exec is split.
DESKTOP_ESCAPE = re.compile(r"\\(.)")
DESKTOP_ESCAPES = {"s": " ", "n": "\n", "t": "\t", "r": "\r", "\\": "\\"}


@dataclass
class Plan:
    """What clean removes, and what it keeps with the reason."""

    paths: list[Path] = field(default_factory=list)
    # Obsolete file mapped to the SHA-1 it was shipped with.
    obsolete_files: dict[Path, str] = field(default_factory=dict)
    backups: list[Path] = field(default_factory=list)
    # Backups of system files: removed only where the user may write.
    system_backups: list[Path] = field(default_factory=list)
    # Obsolete .desktop launcher mapped to the reason it is obsolete.
    launchers: dict[Path, str] = field(default_factory=dict)
    # Launcher mapped to the directory clean searched (applications...).
    launcher_directories: dict[Path, Path] = field(default_factory=dict)
    submodule_sections: list[str] = field(default_factory=list)
    submodule_directories: list[Path] = field(default_factory=list)
    prunable_worktrees: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)

    def needs_confirmation(self) -> bool:
        """Whether the plan removes something that REMOVE must confirm."""
        return bool(
            self.backups
            or self.system_backups
            or self.launchers
            or self.submodule_sections
            or self.submodule_directories
            or self.prunable_worktrees
        )

    def is_empty(self) -> bool:
        return not (self.paths or self.obsolete_files or self.needs_confirmation())


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


def role_obsolete_files(configuration: dict, plan: Plan) -> None:
    """Obsolete role files that still hold the content the role shipped."""
    files = configuration.get("audio_obsolete_files") or {}
    if not files:
        return
    config_home = Path(configuration["audio_config_home"])
    if not config_home.is_absolute():
        raise ValueError("audio_config_home must be an absolute path")
    for relative_path, checksum in sorted(files.items()):
        path = config_home / managed.validate_relative_path(relative_path)
        if managed.has_symlink_component(path.parent):
            plan.kept.append(f"{path}: a parent directory is a link")
            continue
        if not os.path.lexists(path):
            continue
        reason = obsolete_files_module.classify(str(path), str(checksum))
        if reason is None:
            plan.obsolete_files[path] = str(checksum)
        else:
            plan.kept.append(f"{path}: obsolete file that {reason}")


def fstab_mount_points(system_root: Path) -> frozenset[Path]:
    """Mount points /etc/fstab declares, mounted or not."""
    try:
        lines = (system_root / "etc/fstab").read_text().splitlines()
    except FileNotFoundError:
        return frozenset()
    mount_points = set()
    for line in lines:
        fields = line.split()
        if len(fields) >= 2 and not fields[0].startswith("#"):
            # fstab writes a space in a path as \040.
            target = fields[1].replace("\\040", " ")
            if target.startswith("/"):
                mount_points.add(Path(target))
    return frozenset(mount_points)


def absence_is_certain(path: Path, mount_points: frozenset[Path]) -> bool:
    """Whether path is gone, not merely on a filesystem that is not mounted.

    An unmounted fstab entry, a removable medium or an error other than
    "no such file" leaves the absence unproven.
    """
    try:
        os.lstat(path)
        return False
    except FileNotFoundError:
        pass
    except OSError:
        return False
    # A link on the way (~/Games -> /mnt/games) leads to the filesystem that
    # actually holds the path: both spellings are checked.
    for candidate in {path, Path(os.path.realpath(path))}:
        for ancestor in candidate.parents:
            if ancestor in mount_points and not os.path.ismount(ancestor):
                return False
        # A medium that is not plugged in leaves no trace, not even its mount
        # point under /run/media/<user>.
        if any(candidate.is_relative_to(root) for root in REMOVABLE_MEDIA_ROOTS):
            return False
    return True


def read_desktop_entry(path: Path) -> dict[str, str]:
    """Keys of the [Desktop Entry] group; localized keys are left out."""
    entry = {}
    in_group = False
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if line.startswith("["):
            in_group = line == "[Desktop Entry]"
        elif in_group and "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            key = key.strip()
            if "[" not in key:
                entry.setdefault(key, unescape_desktop_value(value.strip()))
    return entry


def unescape_desktop_value(value: str) -> str:
    """Decode the string escapes of the desktop entry format (\\s, \\\\...)."""
    return DESKTOP_ESCAPE.sub(
        lambda match: DESKTOP_ESCAPES.get(match.group(1), match.group(0)), value
    )


def command_search_path(root: Path) -> str:
    directories = os.environ.get("PATH", "").split(os.pathsep)
    directories += [str(root / name) for name in HOME_SEARCH_DIRECTORIES]
    directories += list(LAUNCHER_SEARCH_DIRECTORIES)
    return os.pathsep.join(directory for directory in directories if directory)


def missing_program_reason(
    program: str, root: Path, mount_points: frozenset[Path]
) -> str | None:
    """Why program cannot run, or None when it may (or cannot be judged)."""
    if program.startswith("/"):
        if absence_is_certain(Path(program), mount_points):
            return f"{program} is missing"
        return None
    if "/" in program:
        return None
    if shutil.which(program, path=command_search_path(root)) is None:
        return f"command {program} is not installed"
    return None


def steam_game_installed(app_id: str, root: Path) -> bool | None:
    """Whether a Steam library holds the game; None when that is unknown.

    Every Steam install (native and Flatpak) is searched: the game may come
    from any of them, so it is missing only when all of them can tell.
    """
    found_install = False
    unknown = False
    for steam in STEAM_DIRECTORIES:
        try:
            text = (root / steam / "steamapps/libraryfolders.vdf").read_text()
        except FileNotFoundError:
            continue
        except OSError:
            return None
        found_install = True
        libraries = [
            Path(match.replace("\\\\", "\\"))
            for match in STEAM_LIBRARY_PATH.findall(text)
        ]
        if not libraries:
            unknown = True
        for library in libraries:
            steamapps = library / "steamapps"
            try:
                if (steamapps / f"appmanifest_{app_id}.acf").exists():
                    return True
                if not steamapps.is_dir():
                    # A library on a drive that is not there: unknown.
                    unknown = True
            except OSError:
                unknown = True
    if unknown or not found_install:
        return None
    return False


def launcher_obsolete_reason(
    entry: dict[str, str], root: Path, mount_points: frozenset[Path]
) -> str | None:
    """Why a launcher can no longer start anything, or None."""
    try_exec = entry.get("TryExec")
    if try_exec:
        reason = missing_program_reason(try_exec, root, mount_points)
        if reason:
            return f"TryExec {reason}"
    command = entry.get("Exec")
    if not command:
        return None
    try:
        arguments = shlex.split(command)
    except ValueError:
        return None
    environment = {}
    if arguments and Path(arguments[0]).name == "env":
        arguments = arguments[1:]
        while arguments and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", arguments[0]):
            name, value = arguments.pop(0).split("=", 1)
            environment[name] = value
        if arguments and arguments[0].startswith("-"):
            # env options change how the rest is read: not judged.
            return None
    if not arguments:
        return None
    reason = missing_program_reason(arguments[0], root, mount_points)
    if reason:
        return reason
    prefix = environment.get("WINEPREFIX")
    if (
        prefix
        and prefix.startswith("/")
        and absence_is_certain(Path(prefix), mount_points)
    ):
        return f"Wine prefix {prefix} is missing"
    for argument in arguments[1:]:
        match = STEAM_GAME_URL.match(argument)
        if (
            match
            and int(match.group(1)) < STEAM_APP_ID_LIMIT
            and steam_game_installed(match.group(1), root) is False
        ):
            return f"Steam game {match.group(1)} is not installed"
    return None


def obsolete_launchers(
    root: Path, configuration: dict, system_root: Path, plan: Plan
) -> None:
    """Launchers of the home whose program, prefix or game is gone."""
    root = root.resolve(strict=True)
    if os.geteuid() == 0 and root.stat().st_uid != 0:
        # Root has its own PATH: a command only the owner's PATH finds would
        # look uninstalled, and the MIME cache would be rewritten as root.
        plan.kept.append(
            f"launchers of {root}: checked only when clean runs as their owner"
        )
        return
    _, managed_files = managed.managed_paths(configuration)
    managed_files = set(managed_files)
    mount_points = fstab_mount_points(system_root)
    for relative_directory in LAUNCHER_DIRECTORIES:
        directory = root / relative_directory
        if managed.has_symlink_component(directory) or not directory.is_dir():
            continue
        for parent, _, child_files in os.walk(directory):
            for name in sorted(child_files):
                path = Path(parent) / name
                if not name.endswith(".desktop"):
                    continue
                if path.relative_to(root).as_posix() in managed_files:
                    continue
                if is_broken_link(path):
                    # A broken link outside managed paths is left alone.
                    continue
                try:
                    entry = read_desktop_entry(path)
                except OSError as error:
                    plan.kept.append(f"{path}: unreadable launcher ({error})")
                    continue
                reason = launcher_obsolete_reason(entry, root, mount_points)
                if reason:
                    plan.launchers[path] = reason
                    plan.launcher_directories[path] = directory


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
    # One path per line: a path may contain spaces.
    git_directory, common_directory = result.stdout.splitlines()
    return git_directory == common_directory


def configured_submodules(common_directory: Path) -> list[str]:
    """Names of the submodule.<name> sections of the repository config.

    Every key counts, not only url: a section left with active or update
    alone is still a leftover.
    """
    result = run_git(
        "config",
        "--file",
        str(common_directory / "config"),
        "--name-only",
        "--get-regexp",
        r"^submodule\.",
    )
    # Exit status 1: no such key, so no submodule section.
    if result.returncode not in (0, 1):
        raise RuntimeError("Unable to read the submodules of the Git config")
    # submodule.<name>.<key>: the name may itself contain dots.
    return sorted(
        {
            line[len("submodule.") :].rsplit(".", 1)[0]
            for line in result.stdout.splitlines()
            if line.count(".") >= 2
        }
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
            # A Git directory keeps the clones of its own submodules under
            # modules/; objects, refs and logs hold none and can be large.
            child_directories[:] = [
                name for name in child_directories if name == "modules"
            ]
    return found


def reason_to_keep_clone(git_directory: Path) -> str | None:
    """Why a retired submodule clone holds something found nowhere else."""
    for nested in nested_git_directories(git_directory):
        worktree = run_git("config", "--file", str(nested / "config"), "core.worktree")
        if worktree.returncode == 0:
            checkout = (nested / worktree.stdout.strip()).resolve()
            if checkout.is_dir() and any(checkout.iterdir()):
                return f"its checkout {checkout} still exists"
        # Every ref, stash included, must lead only to commits that a
        # remote-tracking branch or a tag also reaches. --work-tree points at
        # a directory that exists: Git 2.54 (the CI image) still enters core.worktree
        # with --bare, and the old checkout is usually gone.
        unique = run_git(
            "--git-dir",
            str(nested),
            "--work-tree",
            str(nested),
            "rev-list",
            "--all",
            "--not",
            "--remotes",
            "--tags",
            "-n",
            "1",
        )
        if unique.returncode != 0:
            error = unique.stderr.strip().splitlines()
            return f"Git cannot read {nested}" + (f": {error[-1]}" if error else "")
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
    # --literal-pathspecs: a link named "a*" must not match a tracked "ab".
    result = run_git(
        "--literal-pathspecs",
        "ls-files",
        "--error-unmatch",
        "--",
        str(path.relative_to(repository)),
        cwd=repository,
    )
    return result.returncode == 0


def is_separate_tree(directory: Path) -> bool:
    """A nested Git checkout or a Python virtual environment.

    Their content belongs to another repository or to the environment: a
    link this repository does not track may be one the nested clone tracks.
    """
    git_entry = directory / ".git"
    return (
        git_entry.exists()
        or git_entry.is_symlink()
        or (directory / "pyvenv.cfg").is_file()
    )


def repository_files(repository: Path, plan: Plan) -> None:
    """Python caches and untracked broken links of the working tree."""
    for parent, child_directories, child_files in os.walk(repository):
        parent_path = Path(parent)
        for name in list(child_directories):
            path = parent_path / name
            if name in REPOSITORY_SKIPPED_DIRECTORIES or (
                not path.is_symlink() and is_separate_tree(path)
            ):
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


def system_backup_leftovers(system_root: Path, plan: Plan) -> None:
    """Backups of /etc files; those in a directory the user cannot write stay."""
    for backup in managed.find_system_backups(system_root):
        if os.access(backup.parent, os.W_OK):
            plan.system_backups.append(backup)
        else:
            plan.kept.append(f"{backup}: not writable, run clean as root to remove it")


def build_plan(
    root: Path,
    configuration: dict,
    repository: Path,
    system_root: Path = Path("/"),
) -> Plan:
    plan = Plan()
    plan.backups.extend(managed.find_backups(root, configuration))
    system_backup_leftovers(system_root, plan)
    plan.paths.extend(home_broken_links(root, configuration))
    role_obsolete_files(configuration, plan)
    obsolete_launchers(root, configuration, system_root, plan)
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


def refresh_desktop_database(directories: set[Path]) -> None:
    """Drop removed launchers from the MIME cache their directory keeps."""
    program = shutil.which("update-desktop-database")
    for directory in sorted(directories):
        if program is None or not (directory / "mimeinfo.cache").is_file():
            continue
        result = subprocess.run(
            [program, str(directory)],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if result.returncode != 0:
            print(
                f"warning: update-desktop-database {directory} failed",
                file=sys.stderr,
            )


def apply(plan: Plan, repository: Path) -> None:
    for path in plan.backups + plan.system_backups:
        remove_path(path)
    refreshed = set()
    for path in plan.launchers:
        if os.path.lexists(path):
            path.unlink()
        directory = plan.launcher_directories[path]
        # wine/Programs/<game>/ stays behind empty otherwise.
        remove_empty_parents(path, directory)
        refreshed.add(directory)
    refresh_desktop_database(refreshed)
    for path in plan.paths:
        if path.is_symlink():
            if not path.exists():
                path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
    for path, checksum in plan.obsolete_files.items():
        # Checked again: the file may have been edited since it was listed.
        if os.path.lexists(path) and (
            obsolete_files_module.classify(str(path), checksum) is None
        ):
            path.unlink()
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
    for path in plan.backups + plan.system_backups:
        print(f"{verb} backup {path}")
    for path, reason in plan.launchers.items():
        print(f"{verb} obsolete launcher {path} ({reason})")
    for path in plan.paths:
        print(f"{verb} {path}")
    for path in plan.obsolete_files:
        print(f"{verb} obsolete file {path}")
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


def confirmed_items(plan: Plan) -> list[str]:
    """What REMOVE confirms, counted for the prompt and the report."""
    items = []
    if plan.backups or plan.system_backups:
        items.append(f"{len(plan.backups) + len(plan.system_backups)} backups")
    if plan.launchers:
        items.append(f"{len(plan.launchers)} obsolete launchers")
    if plan.submodule_sections or plan.submodule_directories:
        items.append(f"{len(plan.submodule_sections)} retired submodules")
    if plan.prunable_worktrees:
        items.append(f"{len(plan.prunable_worktrees)} worktree records")
    return items


def confirm_removal(plan: Plan, prompt=input, interactive: bool | None = None) -> None:
    """Keep backups and Git metadata unless REMOVE is typed on a terminal."""
    if not plan.needs_confirmation():
        return
    items = ", ".join(confirmed_items(plan))
    if interactive is None:
        interactive = sys.stdin.isatty()
    if not interactive:
        reason = "no terminal to confirm their removal"
    else:
        try:
            answer = prompt(f"Type REMOVE to delete the {items} listed above: ")
        except EOFError:
            answer = ""
        if answer.strip() == "REMOVE":
            return
        reason = "removal not confirmed"
    plan.kept.append(f"{items}: {reason}")
    print(f"keep {plan.kept[-1]}")
    plan.backups.clear()
    plan.system_backups.clear()
    plan.launchers.clear()
    plan.launcher_directories.clear()
    plan.submodule_sections.clear()
    plan.submodule_directories.clear()
    plan.prunable_worktrees.clear()


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
        "--system-root",
        type=Path,
        default=Path("/"),
        help="root whose /etc backups are cleaned (default: /)",
    )
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
        plan = build_plan(root, configuration, repository, arguments.system_root)
        report(plan, arguments.dry_run)
        if not arguments.dry_run:
            confirm_removal(plan)
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
