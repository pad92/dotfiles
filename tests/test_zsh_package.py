"""Build the zsh.tar.gz contents and start Zsh from them.

package_zsh runs scripts/ci/build_zsh_package.py, which lays out the Zsh tree,
.zshenv, a .zshrc rendered from the role template and the plugins of
dotfiles_zsh_plugins. The script is run here against local repositories, never
against GitHub.
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml
from git_fixtures import git, repository

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/ci/build_zsh_package.py"
DEFAULTS = ROOT / "ansible/roles/dotfiles/defaults/main.yml"
ZSH_DEST = ".local/share/dotfiles/zsh"


def commit_plugin(path: Path, name: str) -> str:
    repository(path)
    (path / f"{name}.plugin.zsh").write_text(f"{name.replace('-', '_')}_loaded=1\n")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "pinned")
    pinned = git(path, "rev-parse", "HEAD")
    (path / "later").write_text("later\n")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "later")
    return pinned


def build(home: Path, defaults: Path = DEFAULTS) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(BUILD), "--defaults", str(defaults), str(home)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )


class ZshPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.plugins = {}
        entries = []
        for name in ("zsh-autosuggestions", "zsh-completions"):
            repo = self.work / name
            pinned = commit_plugin(repo, name)
            self.plugins[name] = pinned
            entries.append(
                {
                    "repo": f"file://{repo}",
                    "dest": f"{{{{ dotfiles_zsh_dest }}}}/plugins/{name}",
                    "version": pinned,
                }
            )
        self.defaults = self.work / "defaults.yml"
        self.defaults.write_text(
            yaml.safe_dump(
                {"dotfiles_zsh_dest": ZSH_DEST, "dotfiles_zsh_plugins": entries}
            )
        )
        self.home = self.work / "home"
        self.home.mkdir()

    def test_layout_matches_what_the_role_deploys(self) -> None:
        result = build(self.home, self.defaults)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        self.assertTrue((self.home / ".zshenv").is_file())
        # .zprofile starts the desktop session, so it stays out.
        self.assertFalse((self.home / ".zprofile").exists())
        tree = self.home / ZSH_DEST
        self.assertTrue((tree / "init.zsh").is_file())
        self.assertTrue((tree / "plugins/extract/extract.plugin.zsh").is_file())
        # Only the pinned commit, without Git metadata.
        plugin = tree / "plugins/zsh-completions"
        self.assertTrue((plugin / "zsh-completions.plugin.zsh").is_file())
        self.assertFalse((plugin / "later").exists())
        self.assertEqual(list(tree.rglob(".git")), [])

    def test_zshrc_is_rendered_for_any_home(self) -> None:
        build(self.home, self.defaults)
        text = (self.home / ".zshrc").read_text()

        self.assertNotIn("{{", text)
        self.assertNotIn("{%", text)
        self.assertIn(f'ZSH="${{HOME}}/{ZSH_DEST}"', text)
        self.assertNotIn("ansible_managed", text)

    @unittest.skipUnless(shutil.which("zsh"), "zsh is not installed")
    def test_zsh_starts_from_the_package(self) -> None:
        build(self.home, self.defaults)
        result = subprocess.run(
            ["zsh", "-i", "-c", 'echo "zsh=$ZSH"; echo "plugins=${plugins[*]}"'],
            env={
                "HOME": str(self.home),
                "ZDOTDIR": str(self.home),
                "PATH": "/usr/bin:/bin",
            },
            cwd=self.home,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
            stdin=subprocess.DEVNULL,
        )
        self.assertIn(f"zsh={self.home}/{ZSH_DEST}", result.stdout, result.stderr)
        self.assertIn("zsh-completions", result.stdout)
        self.assertNotRegex(result.stderr, r"no such file|command not found")

    def test_refuses_entries_the_archive_cannot_ship(self) -> None:
        repo = self.work / "zsh-autosuggestions"
        pinned = self.plugins["zsh-autosuggestions"]
        plugins = f"{ZSH_DEST}/plugins"
        cases = {
            "branch": {"dest": f"{plugins}/a", "version": "master"},
            "short hash": {"dest": f"{plugins}/a", "version": pinned[:12]},
            "parent": {"dest": f"{plugins}/../../../../escape", "version": pinned},
            "outside plugins": {"dest": ".zsh/a", "version": pinned},
            "nested": {"dest": f"{plugins}/a/b", "version": pinned},
            "jinja": {"dest": "{{ other }}/a", "version": pinned},
        }
        for name, entry in cases.items():
            with self.subTest(name):
                defaults = self.work / f"{name}.yml"
                defaults.write_text(
                    yaml.safe_dump(
                        {
                            "dotfiles_zsh_dest": ZSH_DEST,
                            "dotfiles_zsh_plugins": [
                                {"repo": f"file://{repo}", **entry}
                            ],
                        }
                    )
                )
                home = self.work / f"home-{name}"
                home.mkdir()

                result = build(home, defaults)

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("Error:", result.stderr)
                self.assertFalse((self.work / "escape").exists())


class ZshPluginDefaultsTests(unittest.TestCase):
    """The role and the archive read the same list, so it must suit both."""

    def test_role_defaults_are_accepted_by_the_archive_builder(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("build_zsh_package", BUILD)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        zsh_dest, plugins = module.load_defaults(DEFAULTS)

        self.assertEqual(zsh_dest, ZSH_DEST)
        self.assertGreaterEqual(len(plugins), 3)
        for plugin in plugins:
            with self.subTest(plugin=plugin["dest"]):
                self.assertRegex(plugin["repo"], r"^https://")
                self.assertEqual(
                    str(Path(plugin["dest"]).parent), f"{ZSH_DEST}/plugins"
                )

    def test_template_has_only_the_two_lines_the_builder_renders(self) -> None:
        text = module_render()
        self.assertNotIn("{{", text)


def module_render() -> str:
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_zsh_package", BUILD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render_zshrc(module.TEMPLATE, ZSH_DEST)


if __name__ == "__main__":
    unittest.main()
