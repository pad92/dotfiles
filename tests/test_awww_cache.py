import os
import runpy
import tempfile
import time
import unittest
from pathlib import Path

PRUNE = runpy.run_path(
    str(
        Path(__file__).parents[1]
        / "ansible/roles/dotfiles/files/home/.bin/awww-cache.py"
    )
)["prune_cache"]


class WallpaperCacheTests(unittest.TestCase):
    def test_expiration_only_deletes_generated_unreferenced_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cache = root / "managed-v1"
            carousel = root / "carousel"
            cache.mkdir()
            carousel.mkdir()
            (cache / "pins").mkdir()
            files = [cache / (character * 64 + ".jpg") for character in "abc"]
            foreign = cache / "personal-photo.jpg"
            foreign.write_bytes(b"photo")
            abandoned = cache / ".awww-render.A1b2C3.jpg"
            abandoned.write_bytes(b"partial render")
            for path in [*files, foreign]:
                path.write_bytes(b"photo")
                os.utime(path, (1, 1))
            (carousel / "current-DP-1").symlink_to(files[0])
            (cache / "pins/awww-DP-2").symlink_to(files[1])
            symlink = cache / ("d" * 64 + ".jpg")
            symlink.symlink_to(foreign)
            PRUNE(cache, carousel, 100, 86400, [])
            self.assertTrue(files[0].exists())
            self.assertTrue(files[1].exists())
            self.assertFalse(files[2].exists())
            self.assertTrue(foreign.exists())
            self.assertTrue(symlink.is_symlink())
            self.assertFalse(abandoned.exists())

    def test_quota_evicts_oldest_and_keeps_current_render(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            files = [cache / (character * 64 + ".jpg") for character in "abc"]
            now = time.time()
            for index, path in enumerate(files):
                path.write_bytes(b"123456")
                os.utime(path, (now - 100 + index, now - 100 + index))
            retained = PRUNE(cache, cache / "missing", 12, 86400, [files[0]])
            self.assertEqual(retained, 12)
            self.assertTrue(files[0].exists())
            self.assertFalse(files[1].exists())
            self.assertTrue(files[2].exists())

    def test_active_images_are_preserved_even_when_over_quota(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            image = cache / ("a" * 64 + ".jpg")
            image.write_bytes(b"active")
            retained = PRUNE(cache, cache / "missing", 1, 86400, [image])
            self.assertEqual(retained, 6)
            self.assertTrue(image.exists())

    def test_symlinked_cache_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "photos"
            target.mkdir()
            cache = root / "managed-v1"
            cache.symlink_to(target)
            with self.assertRaises(ValueError):
                PRUNE(cache, root / "missing", 1, 86400, [])
