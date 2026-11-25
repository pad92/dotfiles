#!/usr/bin/env python3
"""Feeds the audio visualizer label at the bottom of hyprlock.

visualizer.sh starts this daemon from the label. It runs cava, turns each
frame into ROWS lines of Pango markup (stacked block characters colored by
height, like a Winamp spectrum) and writes it to $XDG_RUNTIME_DIR/hyprlock-visualizer/frame. It stops
cava and exits once no hyprlock process of the user is left.
"""

import fcntl
import json
import math
import os
import selectors
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

# Must match the label in hyprlock.conf (the carousel lock screen has none).
# At 48 pt the block glyphs of JetBrains Mono stack without a gap between rows,
# and six rows (516 px) fill about the bottom third of a 1440 px screen.
FONT_SIZE_PT = 48
LETTER_SPACING_PT = 2
ROWS = 6
# JetBrains Mono advance: 600 units of a 1000-unit em. Pango renders points at
# 96 dpi.
ADVANCE_EM = 0.6
PT_TO_PX = 96 / 72
# Extra bars past the edge, which hyprlock clips, so the line always spans
# the whole width.
EXTRA_BARS = 2
FALLBACK_WIDTH = 1920
MAX_BARS = 512
FRAMERATE = 25

STEPS = 8
MAX_LEVEL = ROWS * STEPS
# An empty cell is a no-break space: hyprlock's text_trim strips ordinary
# spaces, which would shift the centered bars.
EMPTY = "\u00a0"
GLYPHS = EMPTY + "▁▂▃▄▅▆▇█"
# Winamp-style spectrum: the color follows the height of the row, bottom row
# first, so quiet bars stay green and only loud ones reach the red. Gruvbox
# Dark, kept in sync with hyprlock.conf. One color per row.
ROW_COLORS = ("#b8bb26", "#b8bb26", "#fabd2f", "#fabd2f", "#fe8019", "#fb4934")
# Faint: the strip is a backdrop behind the clock and the music block.
ALPHA = "20%"

CHECK_INTERVAL_SECONDS = 1.0


def parse_frame(line):
    """Returns the bar levels of a cava ascii frame such as "0;3;24;"."""
    try:
        return [
            min(max(int(value), 0), MAX_LEVEL)
            for value in line.split(";")
            if value.strip()
        ]
    except ValueError:
        return None


def cell(level, row):
    """Returns the glyph and color of a bar at row (0 is the bottom)."""
    full, part = divmod(level, STEPS)
    if row < full:
        return GLYPHS[STEPS], ROW_COLORS[row]
    if row == full and part:
        return GLYPHS[part], ROW_COLORS[row]
    return EMPTY, None


def render_row(levels, row):
    parts = []
    run = []
    run_color = None

    def flush():
        if not run:
            return
        text = "".join(run)
        if run_color is None:
            parts.append(text)
        else:
            parts.append(
                f'<span foreground="{run_color}" fgalpha="{ALPHA}">{text}</span>'
            )
        run.clear()

    for level in levels:
        glyph, color = cell(level, row)
        if color != run_color:
            flush()
            run_color = color
        run.append(glyph)
    flush()
    return "".join(parts)


def render(levels):
    """Returns the ROWS lines of markup of one frame, top row first, or ""
    when every bar is silent."""
    if not any(levels):
        return ""
    rows = "\n".join(render_row(levels, row) for row in reversed(range(ROWS)))
    return f'<span letter_spacing="{LETTER_SPACING_PT * 1024}">{rows}</span>'


def bar_count(width_px):
    """Returns how many bars fill a line of width_px logical pixels."""
    # Measured with PangoCairo: hinting rounds the glyph advance to whole
    # pixels and the letter spacing is truncated (48 pt: 38 + 2 px).
    cell_px = round(FONT_SIZE_PT * ADVANCE_EM * PT_TO_PX) + int(
        LETTER_SPACING_PT * PT_TO_PX
    )
    if width_px <= 0:
        return 1
    return min(math.ceil(width_px / cell_px) + EXTRA_BARS, MAX_BARS)


def widest_monitor(monitors):
    """Returns the widest width in pixels among `hyprctl monitors -j` entries.

    The width is not divided by the monitor scale: hyprlock passes font_size
    to Pango unscaled, so on a scaled output the glyphs may cover as few
    pixels as at scale 1. Too many bars only get clipped, too few would leave
    part of the edge empty.
    """
    widths = []
    for monitor in monitors:
        try:
            width, height = float(monitor["width"]), float(monitor["height"])
            transform = int(monitor.get("transform") or 0)
        except (KeyError, TypeError, ValueError):
            continue
        # Odd transforms rotate the output by 90 or 270 degrees.
        widths.append(height if transform % 2 else width)
    return max(widths, default=FALLBACK_WIDTH)


def monitor_width():
    try:
        result = subprocess.run(
            ["hyprctl", "monitors", "-j"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        return widest_monitor(json.loads(result.stdout))
    except (OSError, subprocess.SubprocessError, ValueError):
        return FALLBACK_WIDTH


def cava_config(bars):
    return f"""[general]
bars = {bars}
framerate = {FRAMERATE}
sleep_timer = 0

[output]
method = raw
raw_target = /dev/stdout
data_format = ascii
ascii_max_range = {MAX_LEVEL}
bar_delimiter = 59
frame_delimiter = 10
"""


def hyprlock_running(proc=None):
    # Tests point HYPRLOCK_VISUALIZER_PROC at a fake process table.
    proc = Path(proc or os.environ.get("HYPRLOCK_VISUALIZER_PROC") or "/proc")
    uid = os.getuid()
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if (
                entry.stat().st_uid == uid
                and (entry / "comm").read_text().strip() == "hyprlock"
            ):
                return True
        except OSError:
            continue
    return False


def runtime_dir():
    """Returns the private state directory, or None when it is unsafe."""
    base = os.environ.get("XDG_RUNTIME_DIR")
    if not base or not os.path.isdir(base) or os.path.islink(base):
        return None
    path = Path(base) / "hyprlock-visualizer"
    try:
        path.mkdir(mode=0o700, exist_ok=True)
        info = path.lstat()
    except OSError:
        return None
    if path.is_symlink() or not path.is_dir() or info.st_uid != os.getuid():
        return None
    path.chmod(0o700)
    return path


def start_time(pid="self"):
    """Returns the start time of a process, field 22 of /proc/<pid>/stat.

    visualizer.sh compares it with the pid file, so a reused pid does not
    pass for a live daemon.
    """
    stat = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    # The command name in parentheses may hold spaces: split after it.
    return stat.rsplit(")", 1)[1].split()[19]


def write_atomic(path, text):
    tmp = path.with_name(f".{path.name}.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


class Daemon:
    def __init__(self, state_dir):
        self.state_dir = state_dir
        self.frame_path = state_dir / "frame"
        self.pid_path = state_dir / "pid"
        self.cava = None
        self.last_frame = None

    def write_frame(self, markup):
        if markup != self.last_frame:
            write_atomic(self.frame_path, markup + "\n")
            self.last_frame = markup

    def cleanup(self, *_args):
        if self.cava and self.cava.poll() is None:
            self.cava.terminate()
            try:
                self.cava.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.cava.kill()
        for path in (self.frame_path, self.pid_path):
            path.unlink(missing_ok=True)
        sys.exit(0)

    def idle(self):
        """Without cava, keeps the pid alive so the label does not respawn us."""
        while hyprlock_running():
            time.sleep(CHECK_INTERVAL_SECONDS)

    def start_cava(self):
        """Returns the running cava, or None when it is missing or fails to
        start. The caller then idles: exiting would remove the pid file and
        the label would start a new daemon, failing the same way, every
        frame."""
        cava = shutil.which("cava")
        if cava is None:
            return None
        config = self.state_dir / "cava.conf"
        try:
            write_atomic(config, cava_config(bar_count(monitor_width())))
            return subprocess.Popen(
                [cava, "-p", str(config)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except OSError as error:
            print(f"hyprlock-visualizer: cannot start cava: {error}", file=sys.stderr)
            return None

    def run(self):
        signal.signal(signal.SIGTERM, self.cleanup)
        signal.signal(signal.SIGINT, self.cleanup)
        write_atomic(self.pid_path, f"{os.getpid()}\n{start_time()}\n")
        self.write_frame("")

        self.cava = self.start_cava()
        if self.cava is None:
            self.idle()
            self.cleanup()

        selector = selectors.DefaultSelector()
        selector.register(self.cava.stdout, selectors.EVENT_READ)
        buffer = b""
        next_check = time.monotonic() + CHECK_INTERVAL_SECONDS
        while True:
            if selector.select(timeout=CHECK_INTERVAL_SECONDS):
                chunk = os.read(self.cava.stdout.fileno(), 65536)
                if not chunk:
                    # cava failed (no audio backend, say): stay alive without
                    # bars rather than let the label respawn us every frame.
                    self.write_frame("")
                    self.idle()
                    break
                buffer += chunk
                *lines, buffer = buffer.split(b"\n")
                # Only the newest complete frame matters.
                if lines:
                    levels = parse_frame(lines[-1].decode("ascii", "replace"))
                    if levels is not None:
                        self.write_frame(render(levels))
            if time.monotonic() >= next_check:
                if not hyprlock_running():
                    break
                next_check = time.monotonic() + CHECK_INTERVAL_SECONDS
        self.cleanup()


def close_inherited_fds():
    """Closes every descriptor past stderr.

    hyprlock runs label commands with the write ends of its output pipes left
    open past stderr. A daemon that kept them would hold the pipes open, so
    hyprlock would wait forever for the first label command to finish and
    never refresh its labels again.
    """
    os.closerange(3, os.sysconf("SC_OPEN_MAX"))


def main():
    close_inherited_fds()
    state_dir = runtime_dir()
    if state_dir is None:
        return 1
    # Held for the daemon's lifetime, so no context manager.
    lock = open(state_dir / "lock", "w")  # noqa: SIM115
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return 0
    Daemon(state_dir).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
