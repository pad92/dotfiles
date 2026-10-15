import fcntl
import os
import shlex
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from jinja2 import Environment

ROOT = Path(__file__).parents[1]
HELPER_TEMPLATE = (
    ROOT
    / "ansible/roles/dotfiles/templates/home/.config/hypr/hyprlock/"
    "carousel-image.sh.j2"
)
EMPTY = ROOT / "ansible/roles/dotfiles/files/home/.config/hypr/hyprlock/empty.png"
AWWW_BIN = ROOT / "ansible/roles/dotfiles/files/home/.bin"


class CarouselTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.helper = self.root / "carousel-image.sh"
        self.helper.write_text(
            Environment().from_string(HELPER_TEMPLATE.read_text()).render(
                ansible_managed="Managed by Ansible",
            )
        )
        self.helper.chmod(0o755)
        self.home = self.root / "home"
        self.user_bin = self.home / ".bin"
        self.user_bin.mkdir(parents=True)
        for script_name in ("awww.sh", "awww-cache.py"):
            (self.user_bin / script_name).symlink_to(AWWW_BIN / script_name)
        self.cache = self.root / "hyprlock-carousel"
        self.cache.mkdir()
        self.local = self.root / "photos"
        self.local.mkdir()
        self.commands = self.root / "bin"
        self.commands.mkdir()
        self.command("awww", "exit 0")
        self.config = self.root / "awww.conf"
        self.config.write_text(
            "WALLPAPER_SOURCE=auto\n"
            f"LOCAL_WALLPAPER_DIRS=({shlex.quote(str(self.local))})\n"
            "REMOTE_WALLPAPER_DIRS=()\n"
            "AWWW_BLURRED_BACKGROUND=false\nAWWW_METADATA_OVERLAY=false\n"
        )
        self.environment = os.environ | {
            "HOME": str(self.home),
            "AWWW_CONFIG_FILE": str(self.config),
            "XDG_CACHE_HOME": str(self.root),
            "PATH": f"{self.commands}:{os.environ['PATH']}",
            "CAROUSEL_TIMEOUT_SECONDS": "6",
        }

    def command(self, name, body):
        script = self.commands / name
        script.write_text(f"#!/bin/sh\n{body}\n")
        script.chmod(0o755)

    def images(self, paths, source="local"):
        (self.cache / "images").write_bytes(
            b"".join(os.fsencode(path) + b"\0" for path in paths)
        )
        (self.cache / "source").write_text(source + "\n")
        (self.cache / "index").write_text("0\n")

    def run_helper(self, *arguments):
        return subprocess.run(
            ["bash", str(self.helper), *arguments],
            env=self.environment,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_missing_and_corrupt_images_are_skipped_without_effects(self):
        corrupt = self.local / "corrupt.jpg"
        corrupt.write_bytes(b"not an image")
        good = self.local / "valid.png"
        shutil.copyfile(EMPTY, good)
        self.images([self.local / "missing.jpg", corrupt, good])
        result = self.run_helper("DP-1", "1920x1080")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.cache / "current-DP-1").resolve(), good)

    def test_attempt_limit_keeps_previous_background_and_advances_index(self):
        current = self.local / "current.png"
        shutil.copyfile(EMPTY, current)
        (self.cache / "current-DP-1").symlink_to(current)
        self.images([self.local / f"missing-{i}.jpg" for i in range(10)])
        result = self.run_helper("DP-1", "1920x1080")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.cache / "index").read_text().strip(), "3")
        self.assertEqual((self.cache / "current-DP-1").resolve(), current)

    def test_slow_remote_read_falls_back_to_local_within_budget(self):
        good = self.local / "valid.png"
        shutil.copyfile(EMPTY, good)
        real_magick = shlex.quote(shutil.which("magick"))
        self.command(
            "magick",
            'case "$*" in *remote-stall*) sleep 30; exit 1;; esac\n'
            f'exec {real_magick} "$@"',
        )
        self.images([self.root / "remote-stall.jpg"], source="remote")
        started = time.monotonic()
        result = self.run_helper("DP-1", "1920x1080")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLess(time.monotonic() - started, 8)
        self.assertEqual((self.cache / "current-DP-1").resolve(), good)
        self.assertEqual((self.cache / "source").read_text().strip(), "local")

    def test_current_path_is_available_while_renderer_holds_lock(self):
        with (self.cache / "lock").open("w") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            started = time.monotonic()
            result = self.run_helper("--current", "DP-1")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertLess(time.monotonic() - started, 1)

    def test_local_stall_is_stopped_by_global_timeout(self):
        self.command("magick", "sleep 30")
        self.images([self.local / "stalled.jpg"])
        started = time.monotonic()
        result = self.run_helper("DP-1", "1920x1080")
        self.assertNotEqual(result.returncode, 0)
        self.assertLess(time.monotonic() - started, 9)

    def test_render_cache_quota_releases_previous_carousel_image(self):
        self.config.write_text(
            self.config.read_text().replace(
                "AWWW_BLURRED_BACKGROUND=false", "AWWW_BLURRED_BACKGROUND=true"
            )
            + "AWWW_RENDER_CACHE_MAX_BYTES=1\n"
        )
        first = self.local / "first.png"
        second = self.local / "second.png"
        shutil.copyfile(EMPTY, first)
        shutil.copyfile(EMPTY, second)
        self.images([first, second])
        result = self.run_helper("DP-1", "64x64")
        self.assertEqual(result.returncode, 0, result.stderr)
        previous = (self.cache / "current-DP-1").resolve()
        self.assertEqual(previous.parent.name, "managed-v1")
        self.assertTrue(previous.is_file())
        result = self.run_helper("DP-1", "64x64")
        self.assertEqual(result.returncode, 0, result.stderr)
        current = (self.cache / "current-DP-1").resolve()
        self.assertNotEqual(current, previous)
        self.assertTrue(current.is_file())
        self.assertFalse(previous.exists())
