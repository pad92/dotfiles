"""Check the names of managed modprobe, modules-load and sysctl drop-ins."""

import re
import tempfile
import unittest
from pathlib import Path

import yaml
from ansible_test_environment import ROOT, ansible_test_environment, run_playbook

ROLES = ROOT / "ansible/roles"
DROP_IN_DIRS = ("/etc/modprobe.d/", "/etc/modules-load.d/", "/etc/sysctl.d/")
VARIABLE = re.compile(r"^\{\{\s*([a-z0-9_.]+)\s*\}\}$")


def walk_tasks(tasks):
    for task in tasks or []:
        yield task
        for key in ("block", "rescue", "always"):
            yield from walk_tasks(task.get(key))


def role_variables(role):
    """Return the role defaults and vars, vars taking precedence."""
    variables = {}
    for name in ("defaults/main.yml", "vars/main.yml"):
        path = role / name
        if path.exists():
            variables.update(yaml.safe_load(path.read_text()) or {})
    return variables


def managed_paths(role):
    """Return the drop-in paths a role writes, with role variables resolved."""
    variables = role_variables(role)
    paths = set()
    for tasks_file in sorted((role / "tasks").glob("*.yml")):
        for task in walk_tasks(yaml.safe_load(tasks_file.read_text())):
            items = task.get("loop")
            if isinstance(items, str) and VARIABLE.match(items):
                items = variables.get(VARIABLE.match(items).group(1))
            if not isinstance(items, list):
                items = [{}]
            for module in (
                "ansible.builtin.template",
                "ansible.builtin.copy",
                "ansible.posix.sysctl",
            ):
                arguments = task.get(module)
                if not isinstance(arguments, dict):
                    continue
                for item in items:
                    path = arguments.get("dest") or arguments.get("sysctl_file")
                    if not isinstance(path, str):
                        continue
                    variable = VARIABLE.match(path)
                    if variable and variable.group(1) == "item.dest":
                        path = (
                            item.get("dest", path) if isinstance(item, dict) else path
                        )
                    elif variable:
                        path = variables.get(variable.group(1), path)
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
        result = run_playbook(
            play,
            cwd=ROOT,
            env=ansible_test_environment(self.work),
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

    def gpu_option_removal(self):
        task = self.extract(
            "gpu/tasks/main.yml",
            "Remove GPU kernel module options the selected profiles do not need",
        )
        files = (ROLES / "gpu/vars/main.yml").read_text()
        task["vars"] = yaml.safe_load(
            files.replace("/etc/modprobe.d", str(self.etc / "modprobe.d"))
        )
        return task

    def test_gpu_removes_options_files_the_profiles_do_not_need(self):
        names = ["modprobe.d/nvidia.conf", "modprobe.d/i915.conf"]
        self.seed(names)
        self.run_task(
            self.gpu_option_removal(),
            {
                "ansible_facts": {"os_family": "Archlinux"},
                "packages_selected_groups": ["01_base", "08_intel_modern"],
                "gpu_i915_enable_guc": None,
            },
        )
        self.assert_migrated(names, [])

    def test_gpu_keeps_options_files_the_profiles_select(self):
        names = ["modprobe.d/nvidia.conf", "modprobe.d/i915.conf"]
        self.seed(names)
        self.run_task(
            self.gpu_option_removal(),
            {
                "ansible_facts": {"os_family": "Archlinux"},
                "packages_selected_groups": ["08_intel_modern", "09_nvidia_modern"],
                "gpu_i915_enable_guc": 3,
            },
        )
        self.assert_migrated([], names)

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
