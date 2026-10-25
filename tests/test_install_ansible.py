import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
FILTER_PATH = ROOT / "ansible/filter_plugins/dotfiles.py"
SPEC = importlib.util.spec_from_file_location("dotfiles_filters", FILTER_PATH)
FILTERS = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(FILTERS)


class PackageStateTests(unittest.TestCase):
    def test_package_groups_use_explicit_then_hostname_then_fact_defaults(self):
        host_groups = {"workstation": ["01_base", "12_containers_docker"]}
        defaults = ["01_base", "03_gtk", "09_nvidia_modern"]
        self.assertEqual(
            FILTERS.select_package_groups(None, "workstation", host_groups, defaults),
            host_groups["workstation"],
        )
        self.assertEqual(
            FILTERS.select_package_groups([], "workstation", host_groups, defaults),
            [],
        )
        self.assertEqual(
            FILTERS.select_package_groups(None, "unknown", host_groups, defaults),
            defaults,
        )

    def test_valid_state_is_normalized(self):
        state = FILTERS.parse_package_state_json(
            json.dumps(
                {
                    "version": 1,
                    "selected_groups": ["03_gtk", "01_base", "01_base"],
                    "owned_packages": ["vim", "git", "vim"],
                }
            )
        )
        self.assertEqual(state["selected_groups"], ["01_base", "03_gtk"])
        self.assertEqual(state["owned_packages"], ["git", "vim"])

    def test_invalid_state_fails_closed(self):
        for content in (
            "not json",
            "[]",
            '{"version":2}',
            '{"version":1,"selected_groups":["bad group"],' '"owned_packages":[]}',
        ):
            with self.subTest(content=content):
                self.assertIsNone(FILTERS.parse_package_state_json(content))

    def test_only_previously_owned_unselected_packages_are_removable(self):
        result = FILTERS.package_removal_candidates(
            ["git", "vim", "old", "linux-custom"],
            ["git"],
            ["git", "vim", "old", "linux-custom"],
        )
        self.assertEqual(result, ["old", "vim"])

    def test_removal_transaction_must_be_safe(self):
        self.assertTrue(FILTERS.safe_removal_preview(["old", "dependency"], ["git"]))
        self.assertFalse(FILTERS.safe_removal_preview(["old", "git"], ["git"]))
        self.assertFalse(FILTERS.safe_removal_preview(["old", "pacman"], []))
        self.assertFalse(FILTERS.safe_removal_preview([], []))


class GraphicsDetectionTests(unittest.TestCase):
    def test_detects_hybrid_controllers(self):
        pci = """00:02.0 VGA compatible controller [0300]: Intel TigerLake [8086:9a49]
01:00.0 3D controller [0302]: NVIDIA GeForce RTX 3070 [10de:2484]
"""
        self.assertEqual(
            FILTERS.detect_graphics_groups(pci),
            ["08_intel_modern", "09_nvidia_modern"],
        )

    def test_unknown_controller_makes_detection_incomplete(self):
        pci = "00:02.0 VGA compatible controller [0300]: Intel TigerLake [8086:9a49]\n"
        pci += "01:00.0 3D controller [0302]: Unknown GPU [10de:9999]\n"
        self.assertEqual(FILTERS.detect_graphics_groups(pci), [])

    def test_sysfs_fallback_identifies_only_all_amd_controllers(self):
        devices = [
            {"class": "0x030000", "vendor": "0x1002", "device": "0x73bf"},
            {"class": "0x020000", "vendor": "0x8086", "device": "0x1234"},
        ]
        self.assertEqual(FILTERS.detect_sysfs_graphics_groups(devices), ["08_amd"])
        devices.append({"class": "0x030200", "vendor": "0x10de", "device": "0x1234"})
        self.assertEqual(FILTERS.detect_sysfs_graphics_groups(devices), [])


class InstallerTargetTests(unittest.TestCase):
    def test_forwards_arguments_to_ansible_playbook(self):
        with tempfile.TemporaryDirectory() as temporary:
            bin_dir = Path(temporary)
            capture = bin_dir / "arguments"
            mock = bin_dir / "ansible-playbook"
            mock.write_text(
                '#!/bin/sh\nprintf \'%s\\n\' "$ANSIBLE_CONFIG" "$@" > "$CAPTURE"\n'
            )
            mock.chmod(0o755)
            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{bin_dir}:{env['PATH']}",
                    "CAPTURE": str(capture),
                }
            )
            result = subprocess.run(
                [
                    "make",
                    "--no-print-directory",
                    "install",
                    f"ANSIBLE_PLAYBOOK={mock}",
                    "ANSIBLE_ARGS=--check -e packages_action=plan",
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = capture.read_text().splitlines()
            self.assertEqual(lines[0], str(ROOT / "ansible.cfg"))
            self.assertEqual(lines[1], str(ROOT / "ansible/site.yml"))
            self.assertEqual(lines[2:], ["--check", "-e", "packages_action=plan"])


if __name__ == "__main__":
    unittest.main()
