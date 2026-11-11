import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from ansible_test_environment import ansible_test_environment

ROOT = Path(__file__).parents[1]
FILTER_PATH = ROOT / "ansible/filter_plugins/dotfiles.py"
SPEC = importlib.util.spec_from_file_location("dotfiles_filters", FILTER_PATH)
FILTERS = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(FILTERS)


class PackageStateTests(unittest.TestCase):
    def test_package_groups_use_explicit_then_host_then_fact_defaults(self):
        host_groups = ["01_base", "12_containers_docker"]
        defaults = ["01_base", "03_gtk", "09_nvidia_modern"]
        self.assertEqual(
            FILTERS.select_package_groups(None, host_groups, defaults), host_groups
        )
        self.assertEqual(FILTERS.select_package_groups([], host_groups, defaults), [])
        # An empty host list is a choice, not a missing one.
        self.assertEqual(FILTERS.select_package_groups(None, [], defaults), [])
        self.assertEqual(FILTERS.select_package_groups(None, None, defaults), defaults)

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
            '{"version":1,"selected_groups":["bad group"],"owned_packages":[]}',
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
                    # Ignore a developer's local .vault so the result is stable.
                    f"DOTFILES_VAULT_PASSWORD_FILE={bin_dir / 'missing-vault'}",
                    "ANSIBLE_ARGS=--check -e packages_action=plan",
                    "HOST=PadsP5560",
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
            # The playbook targets one inventory host over SSH.
            self.assertEqual(
                lines[2:],
                ["--limit", "PadsP5560", "--check", "-e", "packages_action=plan"],
            )


class RepositorySplitTests(unittest.TestCase):
    """Official packages must reach pacman, not the AUR helper."""

    # `pacman -Sl` lines: repository, name, version, optional [installed].
    LISTING = (
        "core acl 2.4.0-1 [installed]\n"
        "extra onnxruntime-cpu 1.29.0-3\n"
        "extra ttf-montserrat 9.000-1\n"
    )

    def test_missing_packages_are_split_by_repository(self):
        tasks = yaml.safe_load(
            (ROOT / "ansible/roles/packages/tasks/install.yml").read_text()
        )
        wanted = {
            "Extract available Arch repository package names",
            "Split Arch packages by repository source",
        }
        selected = [task for task in tasks if task["name"] in wanted]
        self.assertEqual(len(selected), 2)
        selected.append(
            {
                "name": "Show",
                "ansible.builtin.debug": {
                    "msg": "REPO={{ packages_arch_repository | join(',') }}"
                    " AUR={{ packages_arch_aur | join(',') }}"
                },
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            play = work / "play.yml"
            play.write_text(
                yaml.safe_dump(
                    [
                        {
                            "hosts": "localhost",
                            "connection": "local",
                            "gather_facts": False,
                            "vars": {
                                "ansible_facts": {"os_family": "Archlinux"},
                                "packages_selected_groups": ["22_obs"],
                                "packages_missing": [
                                    "obs-backgroundremoval",
                                    "onnxruntime-cpu",
                                    "ttf-montserrat",
                                ],
                                "packages_arch_repository_listing": {
                                    "stdout": self.LISTING
                                },
                            },
                            "tasks": selected,
                        }
                    ]
                )
            )
            result = subprocess.run(
                ["ansible-playbook", "-i", "localhost,", str(play)],
                env=ansible_test_environment(work),
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(
            "REPO=onnxruntime-cpu,ttf-montserrat AUR=obs-backgroundremoval",
            result.stdout,
        )


if __name__ == "__main__":
    unittest.main()
