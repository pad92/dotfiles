import importlib.util
import re
import unittest
from collections import Counter
from pathlib import Path

import yaml

PACKAGE_VARS = Path(__file__).parents[1] / "ansible/roles/packages/vars/archlinux.yml"
DOTFILES_DEFAULTS = (
    Path(__file__).parents[1] / "ansible/roles/dotfiles/defaults/main.yml"
)
MAKO_CONFIG = (
    Path(__file__).parents[1]
    / "ansible/roles/dotfiles/templates/home/.config/mako/config.j2"
)
# Arch package providing the program behind each user unit the dotfiles role
# enables. Adding a unit to the role without listing its package here fails.
GRAPHICAL_UNIT_PACKAGES = {
    "awww.service": "awww",
    "awww_random.timer": "awww",
    "hypridle.service": "hypridle",
    "mako.service": "mako",
    "waybar.service": "waybar",
}
FONT_FAMILY_PACKAGES = {"DejaVu Sans": "ttf-dejavu"}
RECORD_SCRIPT = (
    Path(__file__).parents[1] / "ansible/roles/dotfiles/files/home/.bin/hypr-record.sh"
)
# Arch package providing each command hypr-record.sh needs to record at all.
# Optional helpers (notify-send, wl-copy, xdg-user-dir) are not listed.
RECORD_COMMAND_PACKAGES = {
    "wf-recorder": "wf-recorder",
    "hyprctl": "hyprland",
    "jq": "jq",
    "slurp": "slurp",
}
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
# 22_obs is a standalone profile (ansible/obs.yml) that runs without the base
# and Hyprland groups, so it repeats exactly the runtime OBS needs from them.
OBS_PROFILE_SHARED_PACKAGES = {
    "pipewire-pulse",
    "qt6-wayland",
    "wireplumber",
    "xdg-desktop-portal-hyprland",
}
PROHIBITED_PACKAGE_NAMES = {
    # Conflicts with the power-profiles-daemon selected for gaming.
    "auto-cpufreq",
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

        self.assertEqual(
            duplicates, ALLOWED_CROSS_GROUP_DUPLICATES | OBS_PROFILE_SHARED_PACKAGES
        )

    def test_obs_profile_leaves_the_onnxruntime_provider_free(self):
        # Pinning one provider conflicts with another already installed
        # (onnxruntime-cpu vs onnxruntime-opt-cuda).
        self.assertFalse(
            [name for name in self.groups["22_obs"] if name.startswith("onnxruntime")]
        )

    def test_obs_profile_only_shares_its_declared_runtime(self):
        obs = set(self.groups["22_obs"])
        others = {
            package
            for name, packages in self.groups.items()
            if name != "22_obs"
            for package in packages
        }
        self.assertEqual(obs & others, OBS_PROFILE_SHARED_PACKAGES)
        self.assertTrue(
            {
                "obs-backgroundremoval",
                "obs-studio",
                "simde",
                "ttf-montserrat",
                "v4l2loopback-dkms",
            }.issubset(obs)
        )

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

    def default_group_packages(self):
        default_groups = yaml.safe_load(PACKAGE_VARS.read_text(encoding="utf-8"))[
            "packages_default_groups"
        ]
        return {package for group in default_groups for package in self.groups[group]}

    def test_default_groups_install_every_enabled_graphical_unit(self):
        units = yaml.safe_load(DOTFILES_DEFAULTS.read_text(encoding="utf-8"))[
            "dotfiles_systemd_graphical_units"
        ]
        self.assertEqual(set(units), set(GRAPHICAL_UNIT_PACKAGES))
        installed = self.default_group_packages()
        for unit in units:
            with self.subTest(unit=unit):
                self.assertIn(GRAPHICAL_UNIT_PACKAGES[unit], installed)

    def test_default_groups_install_every_screen_recording_dependency(self):
        script = RECORD_SCRIPT.read_text(encoding="utf-8")
        required = set(re.findall(r"^\s*require (.+)$", script, re.MULTILINE))
        commands = {
            word.strip('"').replace("$RECORDER", "wf-recorder")
            for line in required
            for word in line.split()
        }
        self.assertEqual(commands, set(RECORD_COMMAND_PACKAGES))
        installed = self.default_group_packages()
        for command, package in RECORD_COMMAND_PACKAGES.items():
            with self.subTest(command=command):
                self.assertIn(package, installed)

    def test_default_groups_install_the_notification_font(self):
        font = next(
            line.split("=", 1)[1]
            for line in MAKO_CONFIG.read_text(encoding="utf-8").splitlines()
            if line.startswith("font=")
        )
        family = font.rsplit(" ", 1)[0]
        self.assertIn(family, FONT_FAMILY_PACKAGES)
        self.assertIn(FONT_FAMILY_PACKAGES[family], self.default_group_packages())

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
