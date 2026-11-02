"""Unit tests for edge and error paths of the Ansible Python plugins and modules."""

import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ansible.errors import AnsibleFilterError
from test_ansible_modules import (
    Module,
    Result,
    aur,
    backup,
    files,
    initramfs,
    makepkg,
    submodules,
    sysfs,
    tree,
)

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


filters = load("dotfiles_filters_units", "ansible/filter_plugins/dotfiles.py")
lact = load("lact_filters_units", "ansible/filter_plugins/lact.py")
backups = load("ansible_backups_units", "scripts/ansible_backup_files.py")

NVIDIA_MODERN = "01:00.0 VGA compatible controller [0300]: NVIDIA AD104 [GeForce RTX 4070] [10de:2786]"


class ModuleCase(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def invoke(self, implementation, params, check=False):
        with (
            patch.object(
                implementation, "AnsibleModule", return_value=Module(params, check)
            ),
            self.assertRaises(Result) as caught,
        ):
            implementation.main()
        return caught.exception


class PackageFilterTests(unittest.TestCase):
    def test_group_selection_falls_back_to_defaults_and_replaces_graphics(self):
        self.assertEqual(
            filters.select_package_groups(None, None, {}, ["01_base"]), ["01_base"]
        )
        self.assertEqual(
            filters.select_package_groups(
                None,
                "host",
                {"host": ["01_base", "09_nvidia_legacy"]},
                [],
                ["09_nvidia_modern"],
            ),
            ["01_base", "09_nvidia_modern"],
        )
        # An explicit selection is never rewritten by detection.
        self.assertEqual(
            filters.select_package_groups(
                ["08_amd"], "host", {}, [], ["09_nvidia_modern"]
            ),
            ["08_amd"],
        )

    def test_package_state_rejects_invalid_entries_and_json(self):
        self.assertIsNone(
            filters.parse_package_state(
                {
                    "version": 1,
                    "selected_groups": ["ok"],
                    "owned_packages": ["bad name"],
                }
            )
        )
        self.assertIsNone(filters.parse_package_state_json(None))
        self.assertIsNone(filters.parse_package_state_json("{not json"))
        self.assertEqual(
            filters.parse_package_state_json(
                json.dumps(
                    {"version": 1, "selected_groups": ["b", "a"], "owned_packages": []}
                )
            ),
            {"version": 1, "selected_groups": ["a", "b"], "owned_packages": []},
        )

    def test_graphics_detection_by_vendor_and_generation(self):
        cases = {
            "VGA [0300]: Intel Corporation Haswell [8086:0412]": ["07_intel_legacy"],
            "VGA [0300]: Intel Corporation Alder Lake UHD Graphics [8086:46a6]": [
                "08_intel_modern"
            ],
            "VGA [0300]: NVIDIA GP107 [GeForce GTX 1050] [10de:1c81]": [
                "09_nvidia_legacy"
            ],
            NVIDIA_MODERN: ["09_nvidia_modern"],
            "VGA [0300]: AMD Navi 21 [1002:73bf]": ["08_amd"],
        }
        for listing, expected in cases.items():
            with self.subTest(listing=listing):
                self.assertEqual(filters.detect_graphics_groups(listing), expected)

    def test_graphics_detection_fails_closed_on_unknown_controllers(self):
        for listing in [
            "",
            None,
            "Audio device [0403]: Intel [8086:1234]",
            "VGA [0300]: Intel Corporation Mystery [8086:ffff]",
            "VGA [0300]: NVIDIA Mystery [10de:ffff]",
            "VGA [0300]: Matrox G200 [102b:0522]",
            NVIDIA_MODERN + "\nVGA [0300]: Matrox G200 [102b:0522]",
        ]:
            with self.subTest(listing=listing):
                self.assertEqual(filters.detect_graphics_groups(listing), [])

    def test_graphics_controllers_found_accepts_lspci_and_sysfs_data(self):
        self.assertTrue(filters.graphics_controllers_found(NVIDIA_MODERN))
        self.assertFalse(filters.graphics_controllers_found("Audio [0403]"))
        self.assertTrue(
            filters.graphics_controllers_found([{"class": "0x030000"}, "bad"])
        )
        self.assertFalse(filters.graphics_controllers_found([{"class": "0x040300"}]))
        self.assertFalse(filters.graphics_controllers_found(42))

    def test_sysfs_detection_only_trusts_all_amd_controllers(self):
        amd = {"class": "0x030000", "vendor": "0x1002"}
        intel = {"class": "0x030000", "vendor": "0x8086"}
        self.assertEqual(filters.detect_sysfs_graphics_groups([amd]), ["08_amd"])
        self.assertEqual(filters.detect_sysfs_graphics_groups([amd, intel]), [])
        self.assertEqual(
            filters.detect_sysfs_graphics_groups([{"class": "0x040300"}]), []
        )
        self.assertEqual(filters.detect_sysfs_graphics_groups(None), [])

    def test_protected_packages_include_kernels_and_extras(self):
        self.assertTrue(filters.protected_package("linux-cachyos"))
        self.assertTrue(filters.protected_package("glibc"))
        self.assertFalse(filters.protected_package("jq"))
        self.assertEqual(
            filters.package_removal_candidates(
                ["jq", "extra", "linux-lts", "old"],
                ["jq"],
                ["extra", "linux-lts", "old"],
                ["extra"],
            ),
            ["old"],
        )
        self.assertEqual(filters.package_removal_candidates("jq", [], []), [])

    def test_removal_preview_rejects_protected_desired_or_invalid_values(self):
        self.assertTrue(filters.safe_removal_preview(["old"], []))
        for preview, desired, protected in [
            ([], [], None),
            (["old"], "jq", None),
            (["old", "jq"], ["jq"], None),
            (["old", "keep"], [], ["keep"]),
            (["linux-zen"], [], None),
            (["bad name"], [], None),
        ]:
            with self.subTest(preview=preview):
                self.assertFalse(
                    filters.safe_removal_preview(preview, desired, protected)
                )

    def test_unneeded_graphics_packages_skip_shared_and_selected_groups(self):
        groups = {
            "08_amd": ["vulkan-radeon", "mesa"],
            "09_nvidia_modern": ["nvidia-open", "mesa"],
            "01_base": ["jq"],
        }
        self.assertEqual(
            filters.unneeded_graphics_packages(
                groups,
                ["01_base", "08_amd"],
                ["vulkan-radeon", "mesa", "nvidia-open", "jq"],
                ["vulkan-radeon", "mesa", "jq"],
            ),
            ["nvidia-open"],
        )
        self.assertEqual(filters.unneeded_graphics_packages(None, [], [], []), [])
        self.assertEqual(
            filters.unneeded_graphics_packages({"08_amd": "bad"}, None, None, None),
            [],
        )

    def test_changed_packages_lists_installs_and_version_changes(self):
        before = {
            "same": [{"version": "1", "release": "1", "arch": "x86_64"}],
            "upgraded": [{"version": "1", "release": "1", "arch": "x86_64"}],
            "removed": [{"version": "1", "release": "1", "arch": "x86_64"}],
        }
        after = {
            "same": [{"version": "1", "release": "1", "arch": "x86_64"}],
            "upgraded": [{"version": "2", "release": "1", "arch": "x86_64"}],
            "new": [{"version": "1"}],
            "odd": "not a list",
        }
        self.assertEqual(
            filters.changed_packages(before, after), ["new", "odd", "upgraded"]
        )
        self.assertEqual(filters.changed_packages(None, after), [])

    def test_filter_module_exports_every_filter(self):
        exported = filters.FilterModule().filters()
        self.assertIs(
            exported["package_removal_candidates"], filters.package_removal_candidates
        )
        self.assertEqual(len(exported), 12)
        self.assertEqual(
            set(lact.FilterModule().filters()), {"lact_gpu_ids", "lact_config"}
        )


class LactFilterTests(unittest.TestCase):
    GPU = "1002:73BF-1EAE:6901-0000:03:00.0"

    def config(self, existing=None, **overrides):
        arguments = {
            "gpu_ids": [self.GPU],
            "amd_gpu_ids": [self.GPU],
            "profiles": {"Auto": {"performance_level": "auto"}},
            **overrides,
        }
        return lact.lact_config({} if existing is None else existing, **arguments)

    def test_gpu_listing_ignores_blank_lines(self):
        self.assertEqual(lact.lact_gpu_ids(f"\n0: {self.GPU} (AMD)\n\n"), [self.GPU])

    def test_legacy_profile_names_are_migrated(self):
        result = self.config(
            {
                "version": 7,
                "profiles": {"Balance": {"gpus": {}}},
                "current_profile": "Balance",
            }
        )
        self.assertIn("Auto", result["profiles"])
        self.assertNotIn("Balance", result["profiles"])
        self.assertEqual(result["current_profile"], "Auto")

    def test_profiles_without_selected_vendor_are_skipped(self):
        result = self.config(
            nvidia_gpu_ids=[],
            nvidia_profiles={"NvidiaOnly": {"power_mizer_mode": "Auto"}},
        )
        self.assertNotIn("NvidiaOnly", result["profiles"])

    def test_legacy_profile_does_not_replace_an_existing_profile(self):
        result = self.config(
            {
                "version": 7,
                "profiles": {
                    "Balance": {"gpus": {}},
                    "Auto": {"gpus": {self.GPU: {"performance_level": "high"}}},
                },
                "current_profile": "Auto",
            }
        )
        self.assertEqual(
            result["profiles"]["Auto"]["gpus"][self.GPU]["performance_level"], "high"
        )

    def test_invalid_inputs_are_rejected(self):
        cases = [
            {"amd_gpu_ids": "bad"},
            {"profiles": []},
            {"gpu_ids": ["other"]},
            {"gpu_ids": [self.GPU, self.GPU.lower()]},
            {"profiles": {1: {}}},
            {"profiles": {"Auto": "bad"}},
        ]
        for overrides in cases:
            with (
                self.subTest(overrides=overrides),
                self.assertRaises(AnsibleFilterError),
            ):
                self.config(**overrides)
        for existing in [
            {"version": 7, "gpus": {self.GPU: "bad"}},
            {"version": 7, "profiles": {"Auto": {"gpus": []}}},
        ]:
            with self.subTest(existing=existing), self.assertRaises(AnsibleFilterError):
                self.config(existing)


class ModuleErrorPathTests(ModuleCase):
    def test_aur_reports_inventory_failures(self):
        cases = [
            # pacman -Q fails before anything is installed.
            ([(1, "", "no database")], False),
            # The helper ran but the final inventory cannot be read.
            ([(0, "a 1\n", ""), (127, "new\n", ""), (0, "", ""), (1, "", "x")], True),
        ]
        for side_effect, changed in cases:
            with (
                self.subTest(changed=changed),
                patch.object(
                    Module, "run_command", create=True, side_effect=side_effect
                ),
            ):
                result = self.invoke(aur, {"name": ["new"], "executable": "yay"})
            self.assertTrue(result.failed)
            self.assertEqual(result.data["changed"], changed)

    def test_aur_dependency_check_skips_empty_requests(self):
        self.assertEqual(aur.unsatisfied(Module({}), []), [])

    def test_initramfs_success_reports_changed_files(self):
        image = self.root / "initramfs.img"

        def generate(command, **kwargs):
            self.assertEqual(command, ["mkinitcpio", "-P"])
            image.write_text("new")
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

        with patch.object(initramfs.subprocess, "run", side_effect=generate):
            result = self.invoke(
                initramfs, {"generator": "mkinitcpio", "report_roots": [str(self.root)]}
            )
        self.assertFalse(result.failed)
        self.assertIn(str(image), result.data["changed_files"])

    def test_generators_report_inventory_failures(self):
        for implementation, params in [
            (initramfs, {"generator": "dracut", "report_roots": [str(self.root)]}),
            (makepkg, {"path": str(self.root)}),
        ]:
            name = implementation.__name__
            with self.subTest(module=name, stage="before"):
                with patch.object(files, "snapshot", side_effect=OSError("denied")):
                    result = self.invoke(implementation, params)
                self.assertTrue(result.failed)
                self.assertFalse(result.data["changed"])
            with self.subTest(module=name, stage="after success"):
                with (
                    patch.object(files, "snapshot", side_effect=[{}, OSError("gone")]),
                    patch.object(implementation.subprocess, "run"),
                ):
                    result = self.invoke(implementation, params)
                self.assertTrue(result.failed)
                self.assertFalse(result.data["report_complete"])
            with self.subTest(module=name, stage="after failure"):
                with (
                    patch.object(files, "snapshot", side_effect=[{}, OSError("gone")]),
                    patch.object(
                        implementation.subprocess,
                        "run",
                        side_effect=subprocess.CalledProcessError(1, ["tool"]),
                    ),
                ):
                    result = self.invoke(implementation, params)
                self.assertTrue(result.failed)
                self.assertIn("inventory failed", result.data["msg"])

    def test_makepkg_build_failure_reports_partial_output(self):
        def build(*args, **kwargs):
            (self.root / "partial.log").write_text("log")
            raise subprocess.CalledProcessError(1, ["makepkg"])

        with patch.object(makepkg.subprocess, "run", side_effect=build):
            result = self.invoke(makepkg, {"path": str(self.root)})
        self.assertTrue(result.failed)
        self.assertIn(str(self.root / "partial.log"), result.data["changed_files"])

    def test_snapshot_follows_root_links_skips_missing_and_rejects_fifos(self):
        target = self.root / "target"
        target.mkdir()
        (target / "file").write_text("x")
        link = self.root / "link"
        link.symlink_to(target)
        result = files.snapshot([str(link), str(self.root / "missing")])
        self.assertIn(str(target / "file"), result)
        os.mkfifo(self.root / "fifo")
        with self.assertRaises(OSError):
            files.snapshot([str(self.root)])

    def test_tree_rejects_special_files_and_non_directories(self):
        os.mkfifo(self.root / "fifo")
        result = self.invoke(tree, {"path": str(self.root)})
        self.assertTrue(result.failed)
        self.assertIn("Unsupported", result.data["msg"])
        result = self.invoke(tree, {"path": str(self.root / "fifo")})
        self.assertTrue(result.failed)

    def test_backup_check_mode_and_missing_source(self):
        source = self.root / "source"
        source.mkdir()
        (source / "child").write_text("x")
        planned = self.invoke(
            backup, {"src": str(source), "dest": str(self.root / "dest")}, check=True
        )
        self.assertTrue(planned.data["changed"])
        self.assertIn(str(self.root / "dest/child"), planned.data["changed_files"])
        self.assertTrue(source.exists())
        missing = self.invoke(
            backup, {"src": str(self.root / "missing"), "dest": str(self.root / "b")}
        )
        self.assertTrue(missing.failed)

    def test_backup_refuses_an_existing_destination_before_moving(self):
        source, dest = self.root / "source", self.root / "dest"
        source.write_text("x")
        dest.write_text("old backup")
        result = self.invoke(backup, {"src": str(source), "dest": str(dest)})
        self.assertTrue(result.failed)
        self.assertEqual(dest.read_text(), "old backup")
        self.assertTrue(source.exists())

    def test_backup_requires_renameat2(self):
        with patch.object(backup.ctypes, "CDLL", return_value=object()):
            with self.assertRaises(OSError):
                backup.move_without_replace("a", "b")

    def test_sysfs_unreadable_control_fails(self):
        with patch("builtins.open", side_effect=OSError("denied")):
            result = self.invoke(sysfs, {"path": "/sys/test/control", "value": "x"})
        self.assertTrue(result.failed)
        self.assertIn("cannot read", result.data["msg"])

    def test_sysfs_unverifiable_write_fails(self):
        with patch(
            "builtins.open",
            side_effect=[io.StringIO("old"), io.StringIO(), OSError("gone")],
        ):
            result = self.invoke(sysfs, {"path": "/sys/test/control", "value": "new"})
        self.assertTrue(result.failed)
        self.assertIn("cannot verify", result.data["msg"])

    def test_submodule_failures_are_reported(self):
        error = subprocess.CalledProcessError(1, ["git"])
        with patch.object(submodules, "submodule_revisions", side_effect=error):
            self.assertTrue(
                self.invoke(submodules, {"path": str(self.root)}, check=True).failed
            )
            self.assertTrue(self.invoke(submodules, {"path": str(self.root)}).failed)
        with (
            patch.object(submodules, "submodule_revisions", return_value={}),
            patch.object(submodules.subprocess, "run", side_effect=error),
        ):
            result = self.invoke(submodules, {"path": str(self.root)})
        self.assertTrue(result.failed)
        self.assertFalse(result.data["changed"])
        with (
            patch.object(
                submodules, "submodule_revisions", side_effect=[{}, error, error]
            ),
            patch.object(submodules.subprocess, "run"),
        ):
            result = self.invoke(submodules, {"path": str(self.root)})
        self.assertTrue(result.failed)
        self.assertFalse(result.data["report_complete"])

    def test_unmerged_submodule_is_rejected(self):
        listing = "160000 " + "a" * 40 + " 1\tsub\0"
        with (
            patch.object(
                submodules.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0, stdout=listing),
            ),
            self.assertRaises(ValueError),
        ):
            submodules.submodule_revisions(str(self.root))

    def test_changed_submodule_files_for_new_and_removed_checkouts(self):
        with patch.object(
            submodules.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 0, stdout="a\0b\0"),
        ):
            added = submodules.changed_submodule_files(
                "/repo", {"sub": ("x", False)}, {"sub": ("x", True)}
            )
        self.assertEqual(added, ["/repo/sub/a", "/repo/sub/b"])
        removed = submodules.changed_submodule_files(
            "/repo", {"sub": ("x", True)}, {"sub": ("x", False)}
        )
        self.assertEqual(removed, ["/repo/sub"])


class BackupScriptTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)

    def run_main(self, *arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            patch("sys.argv", ["ansible_backup_files.py", *arguments]),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            code = backups.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def test_inventory_templates_are_trusted_recursively(self):
        value = backups.trust_inventory_templates({"a": ["{{ x }}", 1]})
        self.assertEqual(value["a"][1], 1)
        self.assertEqual(str(value["a"][0]), "{{ x }}")

    def test_load_configuration_resolves_paths_and_hides_errors(self):
        inventory = json.dumps({"dotfiles_files": ["{{ 'custom' }}"]})
        with patch.object(
            backups.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 0, stdout=inventory),
        ) as run:
            result = backups.load_configuration(self.home, ["foo=bar"])
        self.assertEqual(result["dotfiles_files"], ["custom"])
        self.assertIn("foo=bar", run.call_args.args[0])
        for completed in [
            subprocess.CompletedProcess([], 1, stdout="secret"),
            subprocess.CompletedProcess([], 0, stdout="[]"),
            subprocess.CompletedProcess([], 0, stdout="not json"),
        ]:
            with (
                self.subTest(stdout=completed.stdout),
                patch.object(backups.subprocess, "run", return_value=completed),
                self.assertRaises(RuntimeError) as caught,
            ):
                backups.load_configuration(self.home, [])
            self.assertNotIn("secret", str(caught.exception))

    def test_unresolved_or_missing_paths_are_rejected(self):
        with self.assertRaises(ValueError):
            backups.validate_relative_path("{{ unresolved }}")
        configuration = {
            "dotfiles_directories": ["does-not-exist"],
            "dotfiles_links": [],
            "dotfiles_files": [],
            "dotfiles_templates": [],
            "dotfiles_systemd_directory": ".config/systemd",
        }
        with self.assertRaises(RuntimeError):
            backups.managed_paths(configuration)

    def test_main_lists_backups_as_text_and_json(self):
        backup = self.home / ".zshrc.bak"
        configuration = {"dotfiles_files": [".zshrc"]}
        with (
            patch.object(backups, "load_configuration", return_value=configuration),
            patch.object(backups, "find_backups", return_value=[backup]),
        ):
            self.assertEqual(
                self.run_main("list", "--root", str(self.home), "--json")[1].strip(),
                json.dumps([str(backup)]),
            )
            self.assertIn(
                str(backup), self.run_main("list", "--root", str(self.home))[1]
            )
        with (
            patch.object(backups, "load_configuration", return_value=configuration),
            patch.object(backups, "find_backups", return_value=[]),
        ):
            self.assertIn(
                "No Ansible-managed backups",
                self.run_main("list", "--root", str(self.home))[1],
            )

    def test_main_reports_errors(self):
        with patch.object(
            backups, "load_configuration", side_effect=RuntimeError("no inventory")
        ):
            code, _, stderr = self.run_main("list", "--root", str(self.home))
        self.assertEqual(code, 1)
        self.assertIn("no inventory", stderr)
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
            self.run_main("list", "--root", str(self.home / "missing"))


if __name__ == "__main__":
    unittest.main()
