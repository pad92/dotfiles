"""Make must not hand a hook's Git repository variables to its commands."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Identity and signing for the commit made by the test itself; `-c` options do
# not land in the repository config the test inspects afterwards.
COMMIT_OPTIONS = [
    "-c",
    "user.name=Test",
    "-c",
    "user.email=test@example.invalid",
    "-c",
    "commit.gpgsign=false",
]


def clean_env():
    """Return the environment without the variables that select a repository."""
    names = subprocess.run(
        ["git", "rev-parse", "--local-env-vars"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return {k: v for k, v in os.environ.items() if k not in names}


@unittest.skipUnless(shutil.which("make"), "requires make")
class MakefileGitEnvTests(unittest.TestCase):
    def test_hook_in_linked_worktree_cannot_reinitialise_the_repository(self):
        """A pre-commit hook in a linked worktree gets GIT_DIR from Git. A test
        run by `make test` that creates its own repository with `git init`
        then reinitialised the real one instead: core.bare=true, and the
        test's user.name and commit.gpgsign landed in .git/config."""
        env = clean_env()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            main = tmp_path / "main"
            victim = tmp_path / "victim"

            def git(*args, cwd=main):
                return subprocess.run(
                    ["git", *COMMIT_OPTIONS, *args],
                    cwd=cwd,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout

            main.mkdir()
            git("init", "-q")
            shutil.copy(ROOT / "Makefile", main / "Makefile")
            git("add", "Makefile")
            git("commit", "-q", "-m", "init")
            git("worktree", "add", "-q", str(tmp_path / "wt"), "-b", "side")
            config_before = (main / ".git/config").read_text()

            # Stand-in for a test run by the `test` hook: it creates and
            # configures a repository of its own.
            probe = (
                f"probe: ; git init -q {victim} "
                f"&& git -C {victim} config user.name Probe"
            )
            hook = main / ".git/hooks/pre-commit"
            hook.write_text(f"#!/bin/sh\nexec make -s --eval '{probe}' probe\n")
            hook.chmod(0o755)

            git("commit", "-q", "--allow-empty", "-m", "x", cwd=tmp_path / "wt")

            self.assertEqual((main / ".git/config").read_text(), config_before)
            self.assertEqual(git("rev-parse", "--is-bare-repository"), "false\n")
            # The probe's own repository did receive its setting.
            self.assertEqual(
                git("config", "--file", str(victim / ".git/config"), "user.name"),
                "Probe\n",
            )


if __name__ == "__main__":
    unittest.main()
