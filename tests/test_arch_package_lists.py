import importlib.util
import re
import unittest
from collections import Counter
from pathlib import Path

import yaml

PACKAGE_VARS = Path(__file__).parents[1] / "ansible/roles/packages/vars/archlinux.yml"
CACHYOS_VARS = Path(__file__).parents[1] / "ansible/roles/packages/vars/cachyos.yml"
FILTER_PATH = Path(__file__).parents[1] / "ansible/filter_plugins/dotfiles.py"
SPEC = importlib.util.spec_from_file_location("dotfiles_filters", FILTER_PATH)
FILTERS = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(FILTERS)
PACKAGE_NAME = re.compile(r"^[a-z0-9@._+-]+$")
ALLOWED_CROSS_GROUP_DUPLICATES = {
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
    "tlp",
    "xf86-video-intel",
}


class ArchPackageGroupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.groups = yaml.safe_load(PACKAGE_VARS.read_text(encoding="utf-8"))[
            "packages_family_groups"
        ]["Archlinux"]

    def test_lists_are_sorted_unique_and_well_formed(self):
        for group_name, packages in self.groups.items():
            with self.subTest(group=group_name):
                self.assertTrue(packages, "package group must not be empty")
                self.assertEqual(packages, sorted(packages))
                self.assertEqual(len(packages), len(set(packages)))
                self.assertTrue(all(PACKAGE_NAME.fullmatch(pkg) for pkg in packages))

    def test_only_hardware_profile_overlaps_are_allowed(self):
        packages = [package for group in self.groups.values() for package in group]
        duplicates = {
            package for package, count in Counter(packages).items() if count > 1
        }

        self.assertEqual(duplicates, ALLOWED_CROSS_GROUP_DUPLICATES)

    def test_prohibited_package_names_are_not_reintroduced(self):
        packages = {package for group in self.groups.values() for package in group}
        self.assertTrue(PROHIBITED_PACKAGE_NAMES.isdisjoint(packages))

    def test_steam_contains_the_complete_gaming_stack(self):
        steam = set(self.groups["21_steam"])
        self.assertTrue(
            {
                "ananicy-cpp",
                "power-profiles-daemon",
                "python-gobject",
            }.issubset(steam)
        )
        self.assertTrue(
            {
                "cachyos-ananicy-rules",
                "cachyos-settings",
                "proton-cachyos-slr",
            }.isdisjoint(steam)
        )
        self.assertNotIn("gamemode", steam)
        for name, packages in self.groups.items():
            if name != "21_steam":
                self.assertNotIn("power-profiles-daemon", packages)

    def test_cachyos_only_gaming_packages_are_distribution_overrides(self):
        overrides = yaml.safe_load(CACHYOS_VARS.read_text(encoding="utf-8"))[
            "packages_distribution_family_group_overrides"
        ]
        cachyos_steam = overrides["Archlinux"]["21_steam"]

        self.assertTrue(
            {
                "cachyos-ananicy-rules",
                "cachyos-settings",
                "proton-cachyos-slr",
            }.issubset(cachyos_steam)
        )
        self.assertTrue(set(self.groups["21_steam"]).issubset(cachyos_steam))

    def test_sysfs_fallback_does_not_guess_nvidia_generation(self):
        devices = [{"class": "0x030000", "vendor": "0x10de", "device": "0x1b80"}]
        self.assertEqual(FILTERS.detect_sysfs_graphics_groups(devices), [])

    def test_sysfs_fallback_still_selects_unambiguous_amd_group(self):
        devices = [{"class": "0x030000", "vendor": "0x1002", "device": "0x73df"}]
        self.assertEqual(FILTERS.detect_sysfs_graphics_groups(devices), ["08_amd"])

    def test_lspci_fallback_does_not_guess_unknown_nvidia_generation(self):
        pci_device = "VGA compatible controller [0300] [10de:9999]"
        self.assertEqual(FILTERS.detect_graphics_groups(pci_device), [])

    def test_lspci_fallback_recognizes_a_known_modern_nvidia_gpu(self):
        pci_device = "NVIDIA GeForce RTX 4070 [0300] [10de:2786]"
        self.assertEqual(
            FILTERS.detect_graphics_groups(pci_device), ["09_nvidia_modern"]
        )


if __name__ == "__main__":
    unittest.main()
