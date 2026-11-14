"""make pages builds the documentation site like the Pages jobs, then opens it."""

import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("make"), "requires make")
class MakefilePagesTests(unittest.TestCase):
    def dry_run(self, *arguments):
        return subprocess.run(
            ["make", "--no-print-directory", "-n", "pages", *arguments],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()

    def test_builds_like_ci_then_opens_the_index(self):
        self.assertEqual(
            self.dry_run(),
            [
                "CI=1 sh scripts/ci/build_pages.sh",
                f'xdg-open "{ROOT}/public/index.html"',
            ],
        )

    def test_opener_can_be_replaced(self):
        self.assertEqual(
            self.dry_run("XDG_OPEN=firefox")[-1],
            f'firefox "{ROOT}/public/index.html"',
        )


if __name__ == "__main__":
    unittest.main()
