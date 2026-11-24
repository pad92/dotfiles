import importlib.util
import os
import re
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
HYPRLOCK_DIR = ROOT / "ansible/roles/dotfiles/files/home/.config/hypr/hyprlock"
DAEMON = HYPRLOCK_DIR / "visualizer.py"
LABEL = HYPRLOCK_DIR / "visualizer.sh"
CONFIGS = (
    ROOT / "ansible/roles/dotfiles/templates/home/.config/hypr/hyprlock.conf.j2",
    ROOT / "ansible/roles/dotfiles/files/home/.config/hypr/hyprlock-carousel.conf",
)

spec = importlib.util.spec_from_file_location("hyprlock_visualizer", DAEMON)
visualizer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(visualizer)

NBSP = " "


def wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


class RenderTests(unittest.TestCase):
    def test_parse_frame_clamps_levels_and_skips_the_trailing_delimiter(self):
        top = visualizer.MAX_LEVEL
        self.assertEqual(
            visualizer.parse_frame(f"0;3;{top + 5};-1;{top};"), [0, 3, top, 0, top]
        )

    def test_parse_frame_rejects_garbage(self):
        self.assertIsNone(visualizer.parse_frame("0;x;3;"))

    def test_silence_renders_nothing(self):
        self.assertEqual(visualizer.render([0, 0, 0]), "")

    def test_fire_colors_follow_the_distance_from_the_top_of_each_bar(self):
        yellow, orange, red, _ = visualizer.FIRE
        steps = visualizer.STEPS
        # Bar 1 fills two and a half rows, bar 2 one full row.
        markup = visualizer.render([0, 2 * steps + 4, steps])
        self.assertTrue(markup.startswith('<span letter_spacing="2048">'))
        rows = markup.split("\n")
        self.assertEqual(len(rows), visualizer.ROWS)
        top, middle, bottom = rows[-3:]
        self.assertIn(
            f'{NBSP}<span foreground="{yellow}" fgalpha="65%">▄</span>{NBSP}', top
        )
        self.assertIn(
            f'{NBSP}<span foreground="{orange}" fgalpha="65%">█</span>{NBSP}', middle
        )
        # The full bar has its yellow tip on the bottom row, next to the red base.
        self.assertIn(
            f'<span foreground="{red}" fgalpha="65%">█</span>'
            f'<span foreground="{yellow}" fgalpha="65%">█</span>',
            bottom,
        )
        # No ordinary space: hyprlock's text_trim would strip it and shift the bars.
        self.assertNotIn(" ", re.sub(r"<[^>]*>", "", markup))

    def test_every_row_has_one_cell_per_bar(self):
        levels = [level % (visualizer.MAX_LEVEL + 1) for level in range(80)]
        text = re.sub(r"<[^>]*>", "", visualizer.render(levels))
        self.assertEqual(
            [len(row) for row in text.split("\n")], [len(levels)] * visualizer.ROWS
        )

    def test_tall_bars_keep_the_darkest_red_at_the_base(self):
        self.assertEqual(
            visualizer.cell(visualizer.MAX_LEVEL, 0)[1],
            visualizer.FIRE[visualizer.ROWS - 1],
        )
        self.assertEqual(visualizer.cell(0, 0), (NBSP, None))
        self.assertEqual(visualizer.cell(visualizer.STEPS, 1), (NBSP, None))

    def test_bar_count_fills_the_width_and_is_bounded(self):
        bars = visualizer.bar_count(2560)
        # PangoCairo measured a 10 px cell at 10 pt (8 px glyph + 2 px spacing).
        self.assertGreaterEqual(bars * 10, 2560)
        self.assertLessEqual(bars * 10, 2560 * 1.05)
        self.assertEqual(visualizer.bar_count(0), 1)
        self.assertEqual(visualizer.bar_count(10**6), visualizer.MAX_BARS)

    def test_widest_monitor_uses_logical_rotated_widths(self):
        monitors = [
            {"width": 2560, "height": 1440, "scale": 2.0, "transform": 0},
            {"width": 1080, "height": 1920, "scale": 1.0, "transform": 1},
            {"width": "broken"},
        ]
        self.assertEqual(visualizer.widest_monitor(monitors), 1920)
        self.assertEqual(visualizer.widest_monitor([]), visualizer.FALLBACK_WIDTH)


class ConfigTests(unittest.TestCase):
    def test_label_font_size_matches_the_daemon(self):
        for config in CONFIGS:
            with self.subTest(config=config.name):
                text = config.read_text()
                block = re.search(r"label \{[^}]*visualizer\.sh[^}]*\}", text)
                self.assertIsNotNone(block)
                self.assertIn(
                    f"font_size = {visualizer.FONT_SIZE_PT}\n", block.group(0)
                )
                self.assertIn("valign = bottom", block.group(0))
                # Drawn before every other widget, so it stays underneath.
                self.assertLess(block.start(), text.index("input-field {"))

    def test_bottom_left_widgets_stay_above_the_strip(self):
        text = CONFIGS[0].read_text()
        for block in re.findall(r"(?:label|image) \{[^}]*\}", text):
            if "visualizer.sh" in block or "valign = bottom" not in block:
                continue
            y = int(re.search(r"position = -?\d+, (-?\d+)", block).group(1))
            # The strip is ROWS lines of 18 px (10 pt) above a 2 px margin.
            self.assertGreaterEqual(y, 2 + visualizer.ROWS * 18 + 8, block)


class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(mode=0o700)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.state = self.runtime / "hyprlock-visualizer"
        self.env = {
            **os.environ,
            "XDG_RUNTIME_DIR": str(self.runtime),
            "PATH": f"{self.bin}:{os.environ['PATH']}",
        }
        # hyprctl fails: the daemon falls back to FALLBACK_WIDTH.
        self.write_tool("hyprctl", "exit 1")

    def write_tool(self, name, body):
        tool = self.bin / name
        tool.write_text(f"#!/bin/sh\n{body}\n")
        tool.chmod(0o755)

    def start_fake_hyprlock(self):
        """Lists a hyprlock process in a fake process table, so the tests do
        not depend on a real hyprlock running on the host."""
        entry = self.root / "proc" / "4242"
        entry.mkdir(parents=True)
        (entry / "comm").write_text("hyprlock\n")
        self.env["HYPRLOCK_VISUALIZER_PROC"] = str(entry.parent)
        return entry

    @staticmethod
    def stop_fake_hyprlock(entry):
        shutil.rmtree(entry)

    def test_label_starts_the_daemon_when_it_is_not_running(self):
        marker = self.root / "started"
        fake_daemon = self.root / "daemon"
        fake_daemon.write_text(f"#!/bin/sh\ntouch {marker}\n")
        fake_daemon.chmod(0o755)
        self.state.mkdir()
        (self.state / "pid").write_text("999999999\n")
        (self.state / "frame").write_text("stale\n")

        result = subprocess.run(
            ["sh", str(LABEL)],
            env={**self.env, "HYPRLOCK_VISUALIZER_DAEMON": str(fake_daemon)},
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout, "")
        self.assertTrue(wait_for(marker.exists))

    def test_label_prints_the_frame_of_a_live_daemon(self):
        self.state.mkdir()
        (self.state / "pid").write_text(f"{os.getpid()}\n")
        (self.state / "frame").write_text("<span>top\nmiddle\nbottom</span>")
        result = subprocess.run(
            ["sh", str(LABEL)], env=self.env, capture_output=True, text=True, check=True
        )
        self.assertEqual(result.stdout, "<span>top\nmiddle\nbottom</span>\n")

    def test_daemon_renders_cava_frames_and_exits_with_hyprlock(self):
        self.write_tool("cava", 'printf "0;24;3;\\n"; exec sleep 30')
        hyprlock = self.start_fake_hyprlock()
        daemon = subprocess.Popen([str(DAEMON)], env=self.env)
        self.addCleanup(daemon.wait)
        self.addCleanup(daemon.kill)

        frame = self.state / "frame"
        self.assertTrue(wait_for(lambda: frame.exists() and "█" in frame.read_text()))
        self.assertEqual((self.state / "pid").read_text(), f"{daemon.pid}\n")
        self.assertIn(
            f"bars = {visualizer.bar_count(visualizer.FALLBACK_WIDTH)}\n",
            (self.state / "cava.conf").read_text(),
        )

        # A second instance exits at once: the first holds the lock.
        self.assertEqual(
            subprocess.run(
                [str(DAEMON)], env=self.env, timeout=5, check=False
            ).returncode,
            0,
        )

        self.stop_fake_hyprlock(hyprlock)
        self.assertEqual(daemon.wait(timeout=5), 0)
        self.assertFalse(frame.exists())
        self.assertFalse((self.state / "pid").exists())

    def test_daemon_releases_pipes_inherited_from_hyprlock(self):
        # hyprlock leaves the write end of its label pipe open past stderr and
        # waits for EOF on it before it runs the label command again.
        self.write_tool("cava", "exec sleep 30")
        hyprlock = self.start_fake_hyprlock()
        read_end, write_end = os.pipe()
        self.addCleanup(os.close, read_end)
        daemon = subprocess.Popen(
            [str(DAEMON)],
            env=self.env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            pass_fds=(write_end,),
        )
        os.close(write_end)
        self.addCleanup(daemon.wait)
        self.addCleanup(daemon.kill)
        self.assertTrue(wait_for((self.state / "pid").exists))

        os.set_blocking(read_end, False)
        self.assertTrue(wait_for(lambda: self.read_eof(read_end)))
        self.assertIsNone(daemon.poll())
        self.stop_fake_hyprlock(hyprlock)
        self.assertEqual(daemon.wait(timeout=5), 0)

    @staticmethod
    def read_eof(fd):
        try:
            return os.read(fd, 1) == b""
        except BlockingIOError:
            return False

    def test_daemon_without_cava_stays_idle_until_hyprlock_exits(self):
        hyprlock = self.start_fake_hyprlock()
        env = {**self.env, "PATH": f"{self.bin}:/usr/bin"}
        if shutil.which("cava", path="/usr/bin"):
            self.skipTest("cava is installed in /usr/bin")
        daemon = subprocess.Popen([shutil.which("python3"), str(DAEMON)], env=env)
        self.addCleanup(daemon.wait)
        self.addCleanup(daemon.kill)
        self.assertTrue(wait_for((self.state / "pid").exists))
        time.sleep(0.3)
        self.assertIsNone(daemon.poll())
        self.assertEqual((self.state / "frame").read_text(), "\n")
        self.stop_fake_hyprlock(hyprlock)
        self.assertEqual(daemon.wait(timeout=5), 0)


if __name__ == "__main__":
    unittest.main()
