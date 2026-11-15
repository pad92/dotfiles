#!/usr/bin/env python3
"""Lay out the zsh.tar.gz contents in a directory shaped like a home.

The dotfiles role copies the Zsh tree to dotfiles_zsh_dest, renders .zshrc
from a template, copies .zshenv and clones the plugins of dotfiles_zsh_plugins
at pinned commits. The archive must hold the same result without Ansible, so
this script rebuilds it from the same files and reads the plugin list from
the role defaults instead of keeping a copy.

Usage: build_zsh_package.py [--defaults FILE] [--source DIR] HOME

.zprofile is left out: it starts the Hyprland session from a login shell,
which a shell configuration package must not do.
"""

import argparse
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

import yaml

ROOT = Path(__file__).resolve().parents[2]
ROLE = ROOT / "ansible/roles/dotfiles"
DEFAULTS = ROLE / "defaults/main.yml"
SOURCE = ROLE / "files/home"
TEMPLATE = ROLE / "templates/home/.zshrc.j2"
DEST_TOKEN = "{{ dotfiles_zsh_dest }}"
COMMIT = re.compile(r"^[0-9a-f]{40}$")
HOME_FILES = [".zshenv"]


def load_fetch():
    """Reuse the clone-at-a-commit helper of the Vim package."""
    path = Path(__file__).with_name("fetch_vim_plugins.py")
    spec = importlib.util.spec_from_file_location("fetch_vim_plugins", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.fetch


def load_defaults(defaults: Path) -> tuple[str, list[dict[str, str]]]:
    """Return dotfiles_zsh_dest and the plugins, with their dest resolved."""
    data = yaml.safe_load(defaults.read_text()) or {}
    zsh_dest = data.get("dotfiles_zsh_dest")
    plugins = data.get("dotfiles_zsh_plugins")
    if not isinstance(zsh_dest, str) or "{" in zsh_dest:
        raise ValueError(f"{defaults} has no plain dotfiles_zsh_dest")
    if not isinstance(plugins, list) or not plugins:
        raise ValueError(f"{defaults} has no dotfiles_zsh_plugins list")
    resolved = []
    for plugin in plugins:
        if not isinstance(plugin, dict):
            raise ValueError(f"dotfiles_zsh_plugins entry is not a mapping: {plugin!r}")
        repo, dest, version = (plugin.get(k) for k in ("repo", "dest", "version"))
        if not isinstance(repo, str) or not repo:
            raise ValueError(f"dotfiles_zsh_plugins entry has no repo: {plugin!r}")
        # A branch or tag would move without a change to the repository.
        if not isinstance(version, str) or not COMMIT.match(version):
            raise ValueError(f"{repo}: version must be a full commit hash")
        if not isinstance(dest, str):
            raise ValueError(f"{repo}: dest must be a string")
        dest = dest.replace(DEST_TOKEN, zsh_dest)
        path = PurePosixPath(dest)
        plugins_root = PurePosixPath(zsh_dest) / "plugins"
        if "{" in dest or ".." in path.parts or path.parent != plugins_root:
            raise ValueError(f"{repo}: dest must be a path under {plugins_root}/")
        resolved.append({"repo": repo, "dest": dest, "version": version})
    return zsh_dest, resolved


def tracked_files(source: Path, name: str) -> list[Path]:
    """The files Git tracks under source/name, like the role copies."""
    result = subprocess.run(
        ["git", "-C", str(source), "ls-files", "-z", "--", name],
        check=True,
        capture_output=True,
        text=True,
    )
    return [Path(p) for p in result.stdout.split("\0") if p]


def render_zshrc(template: Path, zsh_dest: str) -> str:
    """The template has two Jinja lines: the managed header and ZSH=."""
    lines = []
    for line in template.read_text().splitlines():
        if line.startswith("# {{ ansible_managed }}"):
            line = "# Zsh configuration of https://gitlab.com/pad92/dotfiles"
        elif line.startswith('ZSH="{{ dotfiles_zsh_home }}"'):
            line = f'ZSH="${{HOME}}/{zsh_dest}"'
        lines.append(line)
    text = "\n".join(lines) + "\n"
    if "{{" in text or "{%" in text:
        raise ValueError(f"{template} has Jinja this script does not render")
    return text


def build(home: Path, defaults: Path, source: Path, template: Path) -> None:
    zsh_dest, plugins = load_defaults(defaults)
    fetch = load_fetch()

    for relative in tracked_files(source, "zsh"):
        target = home / zsh_dest / relative.relative_to("zsh")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)
    if not (home / zsh_dest / "init.zsh").is_file():
        raise ValueError(f"no Zsh tree copied from {source}/zsh")

    for name in HOME_FILES:
        shutil.copy2(source / name, home / name)
    (home / ".zshrc").write_text(render_zshrc(template, zsh_dest))

    for plugin in plugins:
        print(f"{plugin['dest']} at {plugin['version']}")
        fetch(plugin, home)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the zsh package contents.")
    parser.add_argument("--defaults", type=Path, default=DEFAULTS)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--template", type=Path, default=TEMPLATE)
    parser.add_argument("home", type=Path)
    arguments = parser.parse_args(argv)
    try:
        build(arguments.home, arguments.defaults, arguments.source, arguments.template)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
