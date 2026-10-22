"""Validate LACT discovery and migration without machine-specific identifiers."""

import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "lact_filters", ROOT / "ansible/filter_plugins/lact.py"
)
LACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LACT)
PROFILES = {
    "Balance": {"performance_level": "auto"},
    "Silence": {"performance_level": "auto"},
    "Jeux-perf": {"performance_level": "high"},
}


class LactConfigTests(unittest.TestCase):
    def test_discovery_keeps_exact_case_and_multiple_devices(self):
        self.assertEqual(
            LACT.lact_gpu_ids(
                "0: GPU-Ab (Test AMD) [Dedicated]\n1: GPU-Cd (Other GPU)\n"
            ),
            ["GPU-Ab", "GPU-Cd"],
        )
        for listing in ["unexpected output", "0: gpu-a (Test)\n1: GPU-A (Duplicate)"]:
            with self.assertRaises(LACT.AnsibleFilterError):
                LACT.lact_gpu_ids(listing)

    def test_migration_preserves_profiles_fans_and_selection(self):
        original = {
            "version": 7,
            "daemon": {"admin_group": "custom-group"},
            "gpus": {"gpu-ab": {"power_cap": 100}},
            "profiles": {
                "Custom": {
                    "gpus": {
                        "gpu-ab": {
                            "fan_control_enabled": True,
                            "fan_control_settings": {"curve": {50: 0.2}},
                        }
                    }
                }
            },
            "current_profile": "Custom",
            "auto_switch_profiles": True,
        }
        untouched = deepcopy(original)
        result = LACT.lact_config(original, ["GPU-Ab"], ["GPU-Ab"], PROFILES)
        self.assertEqual(original, untouched)
        self.assertEqual(result["daemon"], original["daemon"])
        self.assertEqual(result["current_profile"], "Custom")
        self.assertTrue(result["auto_switch_profiles"])
        self.assertEqual(result["gpus"]["GPU-Ab"], original["gpus"]["gpu-ab"])
        self.assertEqual(
            result["profiles"]["Custom"]["gpus"]["GPU-Ab"],
            original["profiles"]["Custom"]["gpus"]["gpu-ab"],
        )
        self.assertEqual(
            LACT.lact_config(result, ["GPU-Ab"], ["GPU-Ab"], PROFILES), result
        )

    def test_new_profiles_only_target_supported_gpus_without_fan_overrides(self):
        result = LACT.lact_config({}, ["GPU-Ab", "GPU-Cd"], ["GPU-Ab"], PROFILES)
        self.assertEqual(result["current_profile"], "Balance")
        for name, profile in result["profiles"].items():
            self.assertEqual(profile["gpus"], {"GPU-Ab": PROFILES[name]})

    def test_custom_profile_names_work_on_first_install(self):
        profiles = {"Quiet": {"performance_level": "auto"}}
        result = LACT.lact_config({}, ["GPU-Ab"], ["GPU-Ab"], profiles)
        self.assertEqual(result["current_profile"], "Quiet")

    def test_empty_profile_defaults_keep_default_mode(self):
        result = LACT.lact_config({}, ["GPU-Ab"], ["GPU-Ab"], {})
        self.assertIsNone(result["current_profile"])

    def test_unknown_or_duplicate_gpu_settings_are_not_reassigned(self):
        for gpus in [{"old-device": {}}, {"gpu-ab": {}, "GPU-Ab": {}}]:
            with self.assertRaises(LACT.AnsibleFilterError):
                LACT.lact_config({"gpus": gpus}, ["GPU-Ab"], ["GPU-Ab"], PROFILES)

    def test_invalid_configs_fail_before_writing(self):
        for config in [
            None,
            [],
            {"version": 99},
            {"profiles": []},
            {"gpus": []},
            {"profiles": {"bad": []}},
            {"current_profile": "missing"},
        ]:
            with self.subTest(config=config), self.assertRaises(
                LACT.AnsibleFilterError
            ):
                LACT.lact_config(config, ["GPU-Ab"], ["GPU-Ab"], PROFILES)
        with self.assertRaises(LACT.AnsibleFilterError):
            LACT.lact_config({}, [], [], PROFILES)


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
class LactDeploymentTests(unittest.TestCase):
    def test_tag_migrates_with_backup_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            role = work / "system"
            shutil.copytree(ROOT / "ansible/roles/system", role)
            tasks = yaml.safe_load((role / "tasks/lact.yml").read_text())
            tasks[0] = {
                "name": "Provide isolated service facts",
                "ansible.builtin.set_fact": {
                    "ansible_facts": {"services": {"lactd.service": {}}}
                },
            }
            tasks[1]["block"][0] = {
                "name": "Simulate running LACT",
                "ansible.builtin.debug": {"msg": "running"},
            }
            for task in tasks[1]["block"][-1]["block"]:
                for module in ["ansible.builtin.file", "ansible.builtin.copy"]:
                    if module in task:
                        task[module].pop("owner", None)
                        task[module].pop("group", None)
            (role / "tasks/lact.yml").write_text(yaml.safe_dump(tasks))
            (role / "handlers/main.yml").write_text(
                yaml.safe_dump(
                    [
                        {
                            "name": "Restart LACT",
                            "ansible.builtin.debug": {"msg": "restart observed"},
                        }
                    ]
                )
            )
            binary = work / "bin"
            binary.mkdir()
            lact = binary / "lact"
            lact.write_text(
                "#!/bin/sh\nif [ \"$*\" = 'cli list' ]; then\n  echo '0: GPU-Ab (Test AMD) [Dedicated]'\nelif [ \"$*\" = 'cli --gpu-id GPU-Ab info' ]; then\n  echo 'Driver Used: amdgpu'\nelse\n  exit 1\nfi\n"
            )
            lact.chmod(0o755)
            config = work / "lact/config.yaml"
            config.parent.mkdir()
            original = {
                "version": 7,
                "profiles": {
                    "Balance": {"gpus": {"gpu-ab": {"performance_level": "auto"}}}
                },
                "current_profile": "Balance",
            }
            config.write_text(yaml.safe_dump(original))
            play = [
                {
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "environment": {"PATH": f"{binary}:{os.environ['PATH']}"},
                    "vars": {"system_lact_config_path": str(config)},
                    "tasks": [
                        {
                            "ansible.builtin.import_role": {
                                "name": str(role),
                                "tasks_from": "lact",
                            },
                            "tags": ["lact"],
                        }
                    ],
                }
            ]
            playbook = work / "play.yml"
            playbook.write_text(yaml.safe_dump(play))

            def run(*arguments, expected_success=True):
                result = subprocess.run(
                    [
                        "ansible-playbook",
                        "-i",
                        "localhost,",
                        str(playbook),
                        "--tags",
                        "lact",
                        *arguments,
                    ],
                    cwd=ROOT,
                    env={**os.environ, "ANSIBLE_LOCAL_TEMP": str(work / "tmp")},
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
                if expected_success:
                    self.assertEqual(
                        result.returncode, 0, result.stdout + result.stderr
                    )
                else:
                    self.assertNotEqual(
                        result.returncode, 0, result.stdout + result.stderr
                    )
                return result.stdout + result.stderr

            run("--check")
            self.assertEqual(yaml.safe_load(config.read_text()), original)
            self.assertFalse(list(config.parent.glob("config.yaml.*~")))
            output = run()
            self.assertIn("restart observed", output)
            migrated = yaml.safe_load(config.read_text())
            self.assertIn("GPU-Ab", migrated["profiles"]["Balance"]["gpus"])
            backups = list(config.parent.glob("config.yaml.*~"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(yaml.safe_load(backups[0].read_text()), original)
            output = run()
            self.assertRegex(output, r"changed=0\b")
            self.assertNotIn("restart observed", output)

            # A system configuration managed through a link must not be replaced.
            linked = work / "external-config.yaml"
            config.rename(linked)
            config.symlink_to(linked)
            original_linked = linked.read_bytes()
            output = run(expected_success=False)
            self.assertIn("regular file", output)
            self.assertTrue(config.is_symlink())
            self.assertEqual(linked.read_bytes(), original_linked)
