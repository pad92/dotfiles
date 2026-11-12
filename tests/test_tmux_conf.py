"""Load .tmux.conf in a private tmux server and read back what it set.

tpm and tmux-sensible are gone: the settings the configuration relied on
from tmux-sensible are written in .tmux.conf itself.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMUX_CONF = ROOT / "ansible/roles/dotfiles/files/home/.tmux.conf"


@unittest.skipUnless(shutil.which("tmux"), "tmux is not installed")
class TmuxConfTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        env = {key: value for key, value in os.environ.items() if key != "TMUX"}
        # The socket lives in the temporary directory: no running server is
        # reached, and none is left behind.
        env.update(HOME=str(self.home), TMUX_TMPDIR=str(self.home))
        self.env = env
        self.addCleanup(self.tmux, "kill-server")

    def tmux(self, *arguments):
        return subprocess.run(
            ["tmux", "-L", "test", "-f", "/dev/null", *arguments],
            env=self.env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    def load(self):
        result = self.tmux("new-session", "-d", ";", "source-file", str(TMUX_CONF))
        self.assertEqual(result.returncode, 0, result.stderr)

    def option(self, scope, name):
        result = self.tmux("show-options", scope, "-v", name)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def binding(self, key):
        result = self.tmux("list-keys", "-T", "prefix", key)
        return result.stdout.strip() if result.returncode == 0 else ""

    def test_loads_without_plugins(self):
        text = TMUX_CONF.read_text()
        self.assertNotIn("@plugin", text)
        self.assertNotIn("tpm", text)
        self.load()
        self.assertEqual(self.tmux("show-options", "-g", "@plugin").stdout, "")

    def test_sets_what_tmux_sensible_used_to(self):
        self.load()
        expected = {
            ("-s", "escape-time"): "0",
            ("-g", "history-limit"): "50000",
            ("-g", "display-time"): "4000",
            ("-g", "status-interval"): "5",
            ("-g", "status-keys"): "emacs",
            ("-s", "focus-events"): "on",
            ("-gw", "aggressive-resize"): "on",
            ("-g", "default-terminal"): "tmux-256color",
        }
        for (scope, name), value in expected.items():
            with self.subTest(option=name):
                self.assertEqual(self.option(scope, name), value)
        # C-a is the prefix: C-b no longer sends itself, and the prefix keys
        # of tmux-sensible that the file did not bind already are there.
        self.assertEqual(self.binding("C-b"), "")
        self.assertIn("previous-window", self.binding("C-p"))
        self.assertIn("next-window", self.binding("C-n"))
        self.assertIn("last-window", self.binding("C-a"))
        self.assertIn("send-prefix", self.binding("a"))

    def test_keeps_every_terminal_override(self):
        # The second override once replaced the list, dropping true color.
        self.load()
        result = self.tmux("show-options", "-g", "-v", "terminal-overrides")
        overrides = result.stdout.splitlines()
        self.assertIn("*:RGB", overrides)
        self.assertIn("xterm*:smcup@:rmcup@", overrides)


if __name__ == "__main__":
    unittest.main()
