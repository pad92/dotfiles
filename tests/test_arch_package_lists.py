import os
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest
from collections import Counter
from pathlib import Path

PACKAGE_DIRECTORY = Path(__file__).parents[1] / "dist" / "arch" / "packages"
BASH = shutil.which("bash")
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

    def test_sysfs_fallback_does_not_guess_nvidia_generation(self):
        install_script = PACKAGE_DIRECTORY.parents[2] / "install"
        with tempfile.TemporaryDirectory() as temporary_directory:
            command_directory = Path(temporary_directory) / "bin"
            command_directory.mkdir()
            device = command_directory / "0000:01:00.0"
            device.mkdir()
            (device / "class").write_text("0x030000\n", encoding="utf-8")
            (device / "vendor").write_text("0x10de\n", encoding="utf-8")
            (device / "device").write_text("0x1b80\n", encoding="utf-8")
            (command_directory / "dirname").symlink_to(shutil.which("dirname"))
            (command_directory / "sort").symlink_to(shutil.which("sort"))
            environment = os.environ | {
                "PATH": str(command_directory),
                "PCI_SYSFS_ROOT": str(command_directory),
            }
            result = subprocess.run(
                [
                    BASH,
                    "-c",
                    f"source {shlex.quote(str(install_script))}; "
                    "if groups=$(detect_graphics_package_groups); then "
                    "printf '%s\\n' \"$groups\"; else printf 'unknown\\n'; fi",
                ],
                check=True,
                capture_output=True,
                text=True,
                env=environment,
            )

        self.assertIn("unknown", result.stdout)

    def test_sysfs_fallback_still_selects_unambiguous_amd_group(self):
        install_script = PACKAGE_DIRECTORY.parents[2] / "install"
        with tempfile.TemporaryDirectory() as temporary_directory:
            command_directory = Path(temporary_directory) / "bin"
            command_directory.mkdir()
            device = command_directory / "0000:01:00.0"
            device.mkdir()
            (device / "class").write_text("0x030000\n", encoding="utf-8")
            (device / "vendor").write_text("0x1002\n", encoding="utf-8")
            (device / "device").write_text("0x73df\n", encoding="utf-8")
            (command_directory / "dirname").symlink_to(shutil.which("dirname"))
            (command_directory / "sort").symlink_to(shutil.which("sort"))
            environment = os.environ | {
                "PATH": str(command_directory),
                "PCI_SYSFS_ROOT": str(command_directory),
            }
            result = subprocess.run(
                [
                    BASH,
                    "-c",
                    f"source {shlex.quote(str(install_script))}; "
                    "detect_graphics_package_groups",
                ],
                check=True,
                capture_output=True,
                text=True,
                env=environment,
            )

        self.assertEqual(result.stdout.strip(), "08_amd")

    def test_lspci_fallback_does_not_guess_unknown_nvidia_generation(self):
        install_script = PACKAGE_DIRECTORY.parents[2] / "install"
        pci_device = "VGA compatible controller [0300] [10de:9999]"
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source {shlex.quote(str(install_script))}; "
                f"detect_graphics_package_groups_from_pci "
                f"{shlex.quote(pci_device)} || printf 'unknown\\n'",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.stdout.strip(), "unknown")

    def test_lspci_fallback_recognizes_a_known_modern_nvidia_gpu(self):
        install_script = PACKAGE_DIRECTORY.parents[2] / "install"
        pci_device = "NVIDIA GeForce RTX 4070 [0300] [10de:2786]"
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source {shlex.quote(str(install_script))}; "
                f"detect_graphics_package_groups_from_pci "
                f"{shlex.quote(pci_device)}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.stdout.strip(), "09_nvidia_modern")


if __name__ == "__main__":
    unittest.main()
