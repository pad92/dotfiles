"""Start Vim on a temporary home and collect what it reports."""

import os
import re
import subprocess
from pathlib import Path

VIM_ERROR = re.compile(r"\bE\d+:")


def start_vim(home: Path, *commands: str) -> str:
    """Start Vim with home/.vimrc, run the Ex commands and return its messages.

    Vim runs as in a session of that home: plugins load as usual, after the
    .vimrc, so :scriptnames lists what a user would get.
    """
    output = home / "messages.txt"
    output.unlink(missing_ok=True)
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
        cwd=home,
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
