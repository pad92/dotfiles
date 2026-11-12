"""Start Vim from the files the vim.tar.gz archive ships.

package_vim archives .vim and .vimrc from ansible/roles/dotfiles/files/home,
which no longer contains Vundle. Vim must start without errors whether or not
Vundle has been cloned into ~/.vim/bundle afterwards.
"""

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from git_fixtures import git

ROOT = Path(__file__).resolve().parents[1]
HOME_FILES = Path("ansible/roles/dotfiles/files/home")
VIM_ERROR = re.compile(r"\bE\d+:")

FAKE_VUNDLE = """\
let g:declared_plugins = []
function! vundle#begin(...) abort
  command! -nargs=+ Plugin call add(g:declared_plugins, <q-args>)
endfunction
function! vundle#end(...) abort
endfunction
"""


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


def start_vim(home: Path, *commands: str) -> str:
    """Start Vim with the copied .vimrc and return its messages."""
    output = home / "messages.txt"
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"VIMINIT", "EXINIT", "VIMRUNTIME", "MYVIMRC"}
    }
    env["HOME"] = str(home)
    subprocess.run(
        [
            "vim",
            "-es",
            "-N",
            "-i",
            "NONE",
            "-u",
            str(home / ".vimrc"),
            f"+redir! > {output}",
            "+silent messages",
            *[f"+{command}" for command in commands],
            "+redir END",
            "+qall!",
        ],
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if not output.is_file():
        raise AssertionError("Vim did not write its messages")
    return output.read_text()


@unittest.skipUnless(shutil.which("vim"), "vim is not installed")
class VimPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        copy_archive_contents(self.home)

    def test_starts_without_errors_when_vundle_is_missing(self) -> None:
        self.assertFalse((self.home / ".vim/bundle/Vundle.vim").exists())

        messages = start_vim(self.home)

        self.assertIsNone(VIM_ERROR.search(messages), messages)

    def test_declares_plugins_when_vundle_is_installed(self) -> None:
        autoload = self.home / ".vim/bundle/Vundle.vim/autoload"
        autoload.mkdir(parents=True)
        (autoload / "vundle.vim").write_text(FAKE_VUNDLE)

        messages = start_vim(self.home, "echo g:declared_plugins")

        self.assertIsNone(VIM_ERROR.search(messages), messages)
        self.assertIn("VundleVim/Vundle.vim", messages)
        self.assertIn("morhetz/gruvbox", messages)


if __name__ == "__main__":
    unittest.main()
