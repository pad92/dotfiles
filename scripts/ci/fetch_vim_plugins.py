#!/usr/bin/env python3
"""Put the pinned Vim plugins into a directory laid out like a home.

The dotfiles role clones the plugins listed in dotfiles_vim_pack_plugins
(ansible/roles/dotfiles/defaults/main.yml) on the target. The vim.tar.gz
archive must ship the same plugins, so the package jobs read the list from
that file instead of keeping a copy of it.

Usage: fetch_vim_plugins.py [--defaults FILE] HOME

Each plugin is cloned into HOME/<dest> at its pinned commit, and its .git
directory is then removed: the archive is unpacked by scripts/vim.sh, which
does not need Git.
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULTS = ROOT / "ansible/roles/dotfiles/defaults/main.yml"
VARIABLE = "dotfiles_vim_pack_plugins"
COMMIT = re.compile(r"^[0-9a-f]{40}$")
PACK_ROOT = PurePosixPath(".vim/pack")


def load_plugins(defaults: Path) -> list[dict[str, str]]:
    """Return the plugin list, refusing entries the archive cannot ship."""
    plugins = (yaml.safe_load(defaults.read_text()) or {}).get(VARIABLE)
    if not isinstance(plugins, list) or not plugins:
        raise ValueError(f"{defaults} has no {VARIABLE} list")
    for plugin in plugins:
        if not isinstance(plugin, dict):
            raise ValueError(f"{VARIABLE} entry is not a mapping: {plugin!r}")
        repo = plugin.get("repo")
        dest = plugin.get("dest")
        version = plugin.get("version")
        if not isinstance(repo, str) or not repo:
            raise ValueError(f"{VARIABLE} entry has no repo: {plugin!r}")
        # A branch or tag would move without a change to the repository.
        if not isinstance(version, str) or not COMMIT.match(version):
            raise ValueError(f"{repo}: version must be a full commit hash")
        # A plain path under .vim/pack: no Jinja, no way out of the archive.
        if not isinstance(dest, str) or "{" in dest:
            raise ValueError(f"{repo}: dest must be a path under {PACK_ROOT}/")
        path = PurePosixPath(dest)
        if (
            ".." in path.parts
            or path.parent == PACK_ROOT
            or not path.is_relative_to(PACK_ROOT)
        ):
            raise ValueError(f"{repo}: dest must be a path under {PACK_ROOT}/")
    return plugins


def fetch(plugin: dict[str, str], home: Path) -> Path:
    """Clone one plugin at its pinned commit and drop its Git metadata."""
    target = home / plugin["dest"]
    if target.exists():
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--quiet", "--no-checkout", "--", plugin["repo"], target],
        check=True,
    )
    subprocess.run(
        ["git", "-C", target, "checkout", "--quiet", "--detach", plugin["version"]],
        check=True,
    )
    head = subprocess.run(
        ["git", "-C", target, "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if head != plugin["version"]:
        raise RuntimeError(f"{target} is at {head}, not {plugin['version']}")
    shutil.rmtree(target / ".git")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch the pinned Vim plugins.")
    parser.add_argument("--defaults", type=Path, default=DEFAULTS)
    parser.add_argument("home", type=Path)
    arguments = parser.parse_args(argv)
    try:
        plugins = load_plugins(arguments.defaults)
        for plugin in plugins:
            print(f"{plugin['dest']} at {plugin['version']}")
            fetch(plugin, arguments.home)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
