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
CONFIG = ROOT / "ansible/roles/dotfiles/templates/home/.config/hypr/hyprlock.conf.j2"
CAROUSEL = (
    ROOT / "ansible/roles/dotfiles/files/home/.config/hypr/hyprlock-carousel.conf"
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

    def test_colors_follow_the_height_of_each_row(self):
        colors = visualizer.ROW_COLORS
        alpha = visualizer.ALPHA
        steps = visualizer.STEPS
        # Bar 1 fills two and a half rows, bar 2 one full row.
        markup = visualizer.render([0, 2 * steps + 4, steps])
        self.assertTrue(markup.startswith('<span letter_spacing="2048">'))
        rows = markup.split("\n")
        self.assertEqual(len(rows), visualizer.ROWS)
        top, middle, bottom = rows[-3:]
        self.assertIn(
            f'{NBSP}<span foreground="{colors[2]}" fgalpha="{alpha}">▄</span>{NBSP}',
            top,
        )
        self.assertIn(
            f'{NBSP}<span foreground="{colors[1]}" fgalpha="{alpha}">█</span>{NBSP}',
            middle,
        )
        # Both bars share the color of the bottom row, whatever their height.
        self.assertIn(
            f'<span foreground="{colors[0]}" fgalpha="{alpha}">██</span>', bottom
        )
        # No ordinary space: hyprlock's text_trim would strip it and shift the bars.
        self.assertNotIn(" ", re.sub(r"<[^>]*>", "", markup))

    def test_every_row_has_its_own_color(self):
        self.assertEqual(len(visualizer.ROW_COLORS), visualizer.ROWS)
        top = visualizer.ROWS - 1
        self.assertEqual(
            visualizer.cell(visualizer.MAX_LEVEL, top)[1], visualizer.ROW_COLORS[-1]
        )
        self.assertEqual(visualizer.cell(0, 0), (NBSP, None))
        self.assertEqual(visualizer.cell(visualizer.STEPS, 1), (NBSP, None))

    def test_frames_hold_only_bar_glyphs(self):
        # No peak marker or other glyph above the bars: only blocks and gaps.
        levels = [level % (visualizer.MAX_LEVEL + 1) for level in range(80)]
        text = re.sub(r"<[^>]*>", "", visualizer.render(levels))
        self.assertLessEqual(set(text) - {"\n"}, set(visualizer.GLYPHS))
        self.assertEqual(visualizer.render([0, 0]), "")

    def test_rows_agree_with_cell_for_every_level(self):
        # render_row reads tables computed once from cell(): reading the color
        # of every cell back from the markup must give the same answer.
        levels = list(range(visualizer.MAX_LEVEL + 1)) * 2
        token = re.compile(r'<span foreground="([^"]+)"[^>]*>|</span>|([^<])')
        for row in range(visualizer.ROWS):
            cells, color = [], None
            for match in token.finditer(visualizer.render_row(levels, row)):
                if match.group(2):
                    cells.append((match.group(2), color))
                else:
                    color = match.group(1)
            self.assertEqual(
                cells, [visualizer.cell(level, row) for level in levels], row
            )

    def test_every_row_has_one_cell_per_bar(self):
        levels = [level % (visualizer.MAX_LEVEL + 1) for level in range(80)]
        text = re.sub(r"<[^>]*>", "", visualizer.render(levels))
        self.assertEqual(
            [len(row) for row in text.split("\n")], [len(levels)] * visualizer.ROWS
        )

    def test_bar_count_fills_the_width_and_is_bounded(self):
        bars = visualizer.bar_count(2560)
        # PangoCairo measured a 40 px cell at 48 pt (38 px glyph + 2 px
        # spacing).
        self.assertGreaterEqual(bars * 40, 2560)
        self.assertLessEqual(bars * 40, 2560 + 2 * 40 + 40)
        self.assertEqual(visualizer.bar_count(0), 1)
        self.assertEqual(visualizer.bar_count(10**6), visualizer.MAX_BARS)

    def test_widest_monitor_uses_rotated_pixel_widths(self):
        monitors = [
            {"width": 1080, "height": 1920, "scale": 1.0, "transform": 1},
            {"width": "broken"},
        ]
        self.assertEqual(visualizer.widest_monitor(monitors), 1920)

    def test_widest_monitor_ignores_the_scale(self):
        # hyprlock does not scale font_size: on a scale 2 output the bars may
        # be as narrow as at scale 1, so they must cover the pixel width.
        monitors = [{"width": 2560, "height": 1440, "scale": 2.0, "transform": 0}]
        self.assertEqual(visualizer.widest_monitor(monitors), 2560)
        self.assertEqual(visualizer.widest_monitor([]), visualizer.FALLBACK_WIDTH)


class ConfigTests(unittest.TestCase):
    def test_label_font_size_matches_the_daemon(self):
        text = CONFIG.read_text()
        block = re.search(r"label \{[^}]*visualizer\.sh[^}]*\}", text)
        self.assertIsNotNone(block)
        self.assertIn(f"font_size = {visualizer.FONT_SIZE_PT}\n", block.group(0))
        self.assertIn("valign = bottom", block.group(0))
        # Drawn before every other widget, so it stays underneath.
        self.assertLess(block.start(), text.index("input-field {"))

    def test_music_block_is_opaque_and_above_the_visualizer(self):
        text = CONFIG.read_text()
        colors = dict(re.findall(r"^(\$\w+) = rgba\((\w{8})\)$", text, re.MULTILINE))
        blocks = re.findall(r"\w+ \{[^}]*playerctlock\.sh[^}]*\}", text)
        self.assertEqual(len(blocks), 6)
        # The visualizer label has the default zindex, 0.
        for block in blocks:
            self.assertRegex(block, r"\n    zindex = [1-9]\d*\n", block)
            color = re.search(r"\n    color = (\$\w+)\n", block)
            if color:
                self.assertTrue(colors[color.group(1)].endswith("ff"), block)

    def test_the_carousel_lock_screen_has_no_visualizer(self):
        self.assertNotIn("visualizer", CAROUSEL.read_text())


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

    def fake_daemon_with_marker(self):
        marker = self.root / "started"
        fake_daemon = self.root / "daemon"
        fake_daemon.write_text(f"#!/bin/sh\ntouch {marker}\n")
        fake_daemon.chmod(0o755)
        return fake_daemon, marker

    def test_label_starts_the_daemon_when_its_pid_was_reused(self):
        # The pid file names a live process, but one that started at another
        # time than the daemon: the pid now belongs to someone else.
        fake_daemon, marker = self.fake_daemon_with_marker()
        self.state.mkdir()
        start = int(visualizer.start_time(os.getpid()))
        (self.state / "pid").write_text(f"{os.getpid()}\n{start + 1}\n")
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

    def test_label_starts_the_daemon_with_busybox_setsid(self):
        # Busybox setsid (Alpine, the CI image) has no -f option and fails on
        # it, so the label must not rely on it.
        self.write_tool(
            "setsid",
            'case "$1" in -*) echo "setsid: unrecognized option" >&2; exit 1 ;; esac\n'
            'exec "$@"',
        )
        fake_daemon, marker = self.fake_daemon_with_marker()

        subprocess.run(
            ["sh", str(LABEL)],
            env={**self.env, "HYPRLOCK_VISUALIZER_DAEMON": str(fake_daemon)},
            check=True,
        )
        self.assertTrue(wait_for(marker.exists))

    def test_label_prints_the_frame_of_a_live_daemon(self):
        self.state.mkdir()
        (self.state / "pid").write_text(
            f"{os.getpid()}\n{visualizer.start_time(os.getpid())}\n"
        )
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
        self.assertEqual(
            (self.state / "pid").read_text(),
            f"{daemon.pid}\n{visualizer.start_time(daemon.pid)}\n",
        )
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

    def test_daemon_stays_idle_when_cava_cannot_start(self):
        # A cava that fails to exec must not crash the daemon: its pid file
        # would be left behind and the label would start a new daemon, failing
        # the same way, every 50 ms.
        self.write_tool("cava", "exit 0")
        (self.bin / "cava").write_text("#!/nonexistent/interpreter\n")
        hyprlock = self.start_fake_hyprlock()
        daemon = subprocess.Popen(
            [str(DAEMON)], env=self.env, stderr=subprocess.DEVNULL
        )
        self.addCleanup(daemon.wait)
        self.addCleanup(daemon.kill)
        self.assertTrue(wait_for((self.state / "pid").exists))
        time.sleep(0.5)
        self.assertIsNone(daemon.poll())
        self.assertTrue((self.state / "pid").exists())
        self.stop_fake_hyprlock(hyprlock)
        self.assertEqual(daemon.wait(timeout=5), 0)
        self.assertFalse((self.state / "pid").exists())

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
