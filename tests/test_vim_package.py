"""Build the vim.tar.gz contents and start Vim from them.

package_vim archives .vim and .vimrc from ansible/roles/dotfiles/files/home,
plus the plugins of dotfiles_vim_pack_plugins that
scripts/ci/fetch_vim_plugins.py clones under .vim/pack. The script is run here
against local repositories, never against GitHub.
"""

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml
from git_fixtures import git, repository
from vim_fixtures import VIM_ERROR, start_vim

ROOT = Path(__file__).resolve().parents[1]
HOME_FILES = Path("ansible/roles/dotfiles/files/home")
FETCH = ROOT / "scripts/ci/fetch_vim_plugins.py"
DEFAULTS = ROOT / "ansible/roles/dotfiles/defaults/main.yml"
START = ".vim/pack/dotfiles/start"


def load_fetch_module():
    spec = importlib.util.spec_from_file_location("fetch_vim_plugins", FETCH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {FETCH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_archive_contents(home: Path) -> None:
    """Copy the tracked files under .vim and .vimrc, as the archive does."""
    tracked = git(
        ROOT, "ls-files", "--", str(HOME_FILES / ".vim"), str(HOME_FILES / ".vimrc")
    ).splitlines()
    copied = 0
    for name in tracked:
        source = ROOT / name
        if not source.is_file():
            continue
        target = home / Path(name).relative_to(HOME_FILES)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied += 1
    if copied == 0 or not (home / ".vimrc").is_file():
        raise AssertionError(f"no Vim configuration copied from {HOME_FILES}")


def commit_files(path: Path, files: dict[str, str], message: str) -> str:
    for name, text in files.items():
        (path / name).parent.mkdir(parents=True, exist_ok=True)
        (path / name).write_text(text)
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", message)
    return git(path, "rev-parse", "HEAD")


def fetch(defaults: Path, home: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FETCH), "--defaults", str(defaults), str(home)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@unittest.skipUnless(shutil.which("vim"), "vim is not installed")
class VimPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.home = self.work / "home"
        self.home.mkdir()
        copy_archive_contents(self.home)

    def test_starts_without_errors_and_without_plugins(self) -> None:
        messages = start_vim(self.home, "scriptnames")

        self.assertIsNone(VIM_ERROR.search(messages), messages)
        self.assertNotIn("/pack/dotfiles/", messages)
        self.assertNotRegex(messages.lower(), r"vundle|/bundle/")

    def test_fetched_plugins_are_pinned_and_load_at_startup(self) -> None:
        colors = self.work / "colors"
        repository(colors)
        colors_pinned = commit_files(
            colors,
            {"colors/gruvbox.vim": "let g:colors_name = 'gruvbox'\n"},
            "pinned",
        )
        commit_files(colors, {"colors/later.vim": '" later\n'}, "later")

        # A plugin with an after directory and a filetype plugin.
        markdown = self.work / "markdown"
        repository(markdown)
        markdown_pinned = commit_files(
            markdown,
            {
                "plugin/fixture.vim": "let g:fixture_plugin = 'pinned'\n",
                "after/plugin/fixture_after.vim": "let g:fixture_after = 1\n",
                "ftplugin/markdown/fixture.vim": "let b:fixture_markdown = 1\n",
            },
            "pinned",
        )
        commit_files(
            markdown,
            {"plugin/fixture.vim": "let g:fixture_plugin = 'later'\n"},
            "later",
        )

        defaults = self.work / "defaults.yml"
        defaults.write_text(
            yaml.safe_dump(
                {
                    "dotfiles_vim_pack_plugins": [
                        {
                            "repo": f"file://{colors}",
                            "dest": f"{START}/colors",
                            "version": colors_pinned,
                        },
                        {
                            "repo": f"file://{markdown}",
                            "dest": f"{START}/markdown",
                            "version": markdown_pinned,
                        },
                    ]
                }
            )
        )

        result = fetch(defaults, self.home)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        start = self.home / START
        self.assertEqual(
            sorted(p.name for p in start.iterdir()), ["colors", "markdown"]
        )
        self.assertEqual(list(start.rglob(".git")), [])
        # The pinned commit, not the branch head.
        self.assertFalse((start / "colors/colors/later.vim").exists())
        self.assertIn("'pinned'", (start / "markdown/plugin/fixture.vim").read_text())

        (self.home / "notes.md").write_text("# notes\n")
        messages = start_vim(
            self.home,
            "edit notes.md",
            "scriptnames",
            "echo 'colors=' . g:colors_name",
            "echo 'plugin=' . g:fixture_plugin",
            "echo 'after=' . g:fixture_after",
            "echo 'markdown=' . b:fixture_markdown",
        )

        self.assertIsNone(VIM_ERROR.search(messages), messages)
        # ui.vim runs :colorscheme before the packages are loaded, which
        # searches 'packpath' as well.
        self.assertIn("colors=gruvbox", messages)
        self.assertIn("plugin=pinned", messages)
        # :help packages: a package's after directory joins 'runtimepath'.
        self.assertIn(f"{START}/markdown/after/plugin/fixture_after.vim", messages)
        self.assertIn("after=1", messages)
        self.assertIn("markdown=1", messages)

    def test_refuses_entries_the_archive_cannot_ship(self) -> None:
        plugin = self.work / "plugin"
        repository(plugin)
        pinned = commit_files(plugin, {"plugin/a.vim": '" a\n'}, "pinned")
        cases = {
            "branch": {"dest": f"{START}/a", "version": "master"},
            "short hash": {"dest": f"{START}/a", "version": pinned[:12]},
            "parent": {"dest": f"{START}/../../../../escape", "version": pinned},
            "absolute": {"dest": str(self.work / "escape"), "version": pinned},
            "outside pack": {"dest": ".vim/plugin/a", "version": pinned},
            "package root": {"dest": ".vim/pack/dotfiles", "version": pinned},
            "jinja": {"dest": "{{ dotfiles_vim_pack }}/a", "version": pinned},
        }
        for name, entry in cases.items():
            with self.subTest(name):
                defaults = self.work / f"{name}.yml"
                defaults.write_text(
                    yaml.safe_dump(
                        {
                            "dotfiles_vim_pack_plugins": [
                                {"repo": f"file://{plugin}", **entry}
                            ]
                        }
                    )
                )
                home = self.work / f"home-{name}"
                home.mkdir()

                result = fetch(defaults, home)

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("Error:", result.stderr)
                self.assertEqual(list(home.iterdir()), [])
                self.assertFalse((self.work / "escape").exists())

        defaults = self.work / "empty.yml"
        defaults.write_text("dotfiles_zsh_plugins: []\n")
        self.assertEqual(fetch(defaults, self.home).returncode, 1)


class VimPackDefaultsTests(unittest.TestCase):
    """The role and the archive read the same list, so it must suit both."""

    def test_role_defaults_are_pinned_plugins_under_the_start_directory(self):
        plugins = load_fetch_module().load_plugins(DEFAULTS)
        names = [Path(plugin["dest"]).name for plugin in plugins]
        self.assertEqual(len(names), len(set(names)), names)
        for plugin in plugins:
            with self.subTest(plugin=plugin["dest"]):
                self.assertEqual(str(Path(plugin["dest"]).parent), START)
                self.assertRegex(plugin["repo"], r"^https://")
                # A tracked file there would be copied into the clone.
                self.assertFalse(
                    git(ROOT, "ls-files", "--", str(HOME_FILES / plugin["dest"]))
                )


if __name__ == "__main__":
    unittest.main()
