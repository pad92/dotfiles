"""Throwaway Git repositories for tests.

make test drops the GIT_* variables a hook exports, so -C selects the
fixture rather than the repository under test.
"""

import subprocess
from pathlib import Path


def git(path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def repository(path: Path) -> None:
    """Create an empty repository that commits without a key or a user."""
    path.mkdir(parents=True)
    git(path, "init", "-q")
    git(path, "config", "commit.gpgsign", "false")
    git(path, "config", "user.name", "Test")
    git(path, "config", "user.email", "test@example.invalid")
