"""Check the names of managed modprobe, modules-load and sysctl drop-ins."""

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from ansible_test_environment import ansible_test_environment

ROOT = Path(__file__).resolve().parents[1]
ROLES = ROOT / "ansible/roles"
DROP_IN_DIRS = ("/etc/modprobe.d/", "/etc/modules-load.d/", "/etc/sysctl.d/")
VARIABLE = re.compile(r"^\{\{\s*([a-z0-9_]+)\s*\}\}$")


def walk_tasks(tasks):
    for task in tasks or []:
        yield task
        for key in ("block", "rescue", "always"):
            yield from walk_tasks(task.get(key))


def managed_paths(role):
    """Return the drop-in paths a role writes, with defaults resolved."""
    defaults_file = role / "defaults/main.yml"
    defaults = (
        yaml.safe_load(defaults_file.read_text()) if defaults_file.exists() else {}
    )
    paths = set()
    for tasks_file in sorted((role / "tasks").glob("*.yml")):
        for task in walk_tasks(yaml.safe_load(tasks_file.read_text())):
            for module in (
                "ansible.builtin.template",
                "ansible.builtin.copy",
                "ansible.posix.sysctl",
            ):
                arguments = task.get(module)
                if not isinstance(arguments, dict):
                    continue
                path = arguments.get("dest") or arguments.get("sysctl_file")
                if not isinstance(path, str):
                    continue
                variable = VARIABLE.match(path)
                if variable:
                    path = defaults.get(variable.group(1), path)
                if path.startswith(DROP_IN_DIRS):
                    paths.add(path)
    return paths


class DropInNameTests(unittest.TestCase):
    def test_managed_drop_ins_use_plain_names(self):
        found = {}
        for role in sorted(path for path in ROLES.iterdir() if path.is_dir()):
            for path in managed_paths(role):
                found[path] = role.name
        # Guard the scan itself: an empty or partial result would pass vacuously.
        self.assertTrue(
            {
                "/etc/sysctl.d/60-hardening.conf",
                "/etc/sysctl.d/70-bpf.conf",
                "/etc/modprobe.d/nvidia.conf",
                "/etc/modprobe.d/i915.conf",
                "/etc/modprobe.d/v4l2loopback.conf",
                "/etc/modules-load.d/v4l2loopback.conf",
                "/etc/modprobe.d/power-save.conf",
                "/etc/modprobe.d/iwlwifi.conf",
            }
            <= set(found),
            sorted(found),
        )
        for path, role in found.items():
            name = Path(path).name
            with self.subTest(path=path, role=role):
                self.assertFalse(name.startswith(("zz-", "00-")), path)
                self.assertNotIn("dotfiles", name)


class DropInMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.etc = self.work / "etc"
        for directory in ("modprobe.d", "modules-load.d"):
            (self.etc / directory).mkdir(parents=True)

    def extract(self, tasks_file, name):
        tasks = yaml.safe_load((ROLES / tasks_file).read_text())
        task = next(task for task in walk_tasks(tasks) if task.get("name") == name)
        task.pop("notify", None)
        task.pop("tags", None)
        return yaml.safe_load(
            yaml.safe_dump(task)
            .replace("/etc/modprobe.d", str(self.etc / "modprobe.d"))
            .replace("/etc/modules-load.d", str(self.etc / "modules-load.d"))
        )

    def run_task(self, task, variables):
        play = self.work / "play.yml"
        play.write_text(
            yaml.safe_dump(
                [
                    {
                        "hosts": "localhost",
                        "connection": "local",
                        "gather_facts": False,
                        "vars": variables,
                        "tasks": [task],
                    }
                ]
            )
        )
        result = subprocess.run(
            ["ansible-playbook", "-i", "localhost,", str(play)],
            cwd=ROOT,
            env=ansible_test_environment(self.work),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def seed(self, names):
        for name in names:
            (self.etc / name).write_text(f"old {name}\n")

    def assert_migrated(self, removed, kept):
        for name in removed:
            self.assertFalse((self.etc / name).exists(), name)
        for name in kept:
            self.assertEqual((self.etc / name).read_text(), f"old {name}\n")

    def test_gpu_removes_options_files_with_earlier_names(self):
        removed = [
            "modprobe.d/zz-dotfiles-gpu.conf",
            "modprobe.d/zz-dotfiles-i915.conf",
        ]
        kept = ["modprobe.d/nvidia.conf", "modprobe.d/i915.conf"]
        self.seed(removed + kept)
        self.run_task(
            self.extract(
                "gpu/tasks/main.yml",
                "Remove GPU module options written under earlier names",
            ),
            {
                "ansible_facts": {"os_family": "Archlinux"},
                "packages_selected_groups": ["01_base"],
            },
        )
        self.assert_migrated(removed, kept)

    def test_obs_removes_v4l2loopback_files_with_earlier_names(self):
        removed = [
            "modprobe.d/zz-dotfiles-v4l2loopback.conf",
            "modules-load.d/zz-dotfiles-v4l2loopback.conf",
        ]
        kept = ["modprobe.d/v4l2loopback.conf", "modules-load.d/v4l2loopback.conf"]
        self.seed(removed + kept)
        self.run_task(
            self.extract(
                "obs/tasks/virtualcam.yml",
                "Remove v4l2loopback files written under earlier names",
            ),
            {},
        )
        self.assert_migrated(removed, kept)


if __name__ == "__main__":
    unittest.main()
