import re
import unittest
from collections import Counter
from pathlib import Path

PACKAGE_DIRECTORY = Path(__file__).parents[1] / "dist" / "arch" / "packages"
PACKAGE_NAME = re.compile(r"^[a-z0-9@._+-]+$")
ALLOWED_CROSS_FILE_DUPLICATES = {
    "libva-nvidia-driver",
    "nvidia-container-toolkit",
    "nvidia-prime",
}
PROHIBITED_PACKAGE_NAMES = {
    "hunspell-fr",
    "lib32-libvdpau",
    "libva-vdpau-driver",
    "man",
    "mlocate",
    "p7zip",
    "power-profiles-daemon",
    "tlp",
    "xf86-video-intel",
}


class ArchPackageListTests(unittest.TestCase):
    def test_lists_are_sorted_unique_and_well_formed(self):
        for package_file in sorted(PACKAGE_DIRECTORY.glob("*.txt")):
            with self.subTest(package_file=package_file.name):
                packages = package_file.read_text(encoding="utf-8").splitlines()

                self.assertTrue(packages, "package list must not be empty")
                self.assertEqual(packages, sorted(packages))
                self.assertEqual(len(packages), len(set(packages)))
                self.assertTrue(all(PACKAGE_NAME.fullmatch(pkg) for pkg in packages))

    def test_only_hardware_profile_overlaps_are_allowed(self):
        packages = [
            package
            for package_file in PACKAGE_DIRECTORY.glob("*.txt")
            for package in package_file.read_text(encoding="utf-8").splitlines()
        ]
        duplicates = {
            package for package, count in Counter(packages).items() if count > 1
        }

        self.assertEqual(duplicates, ALLOWED_CROSS_FILE_DUPLICATES)

    def test_prohibited_package_names_are_not_reintroduced(self):
        packages = {
            package
            for package_file in PACKAGE_DIRECTORY.glob("*.txt")
            for package in package_file.read_text(encoding="utf-8").splitlines()
        }

        self.assertTrue(PROHIBITED_PACKAGE_NAMES.isdisjoint(packages))


if __name__ == "__main__":
    unittest.main()
