"""Exercise optional X3D controls with arbitrary sysfs device instance names."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
class X3dDiscoveryTests(unittest.TestCase):
    def test_discovered_controls_check_mode_and_opt_out(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            driver = work / "driver"
            driver.mkdir()
            controls = []
            for index, name in enumerate(["arbitrary-instance", "another-instance"]):
                device = work / f"device{index}"
                device.mkdir()
                control = device / "amd_x3d_mode"
                control.write_text("frequency\n")
                controls.append(control)
                (driver / name).symlink_to(device, target_is_directory=True)
            all_tasks = yaml.safe_load(
                (
                    ROOT / "ansible/roles/system/tasks/amd_cpu_performance.yml"
                ).read_text()
            )
            start = next(
                index
                for index, task in enumerate(all_tasks)
                if task["name"] == "Check for the AMD X3D driver"
            )
            tasks = all_tasks[start:]
            tasks[0]["ansible.builtin.stat"]["path"] = str(driver)
            tasks[1]["ansible.builtin.command"]["argv"][2] = str(driver)
            play = [
                {
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {"system_amd_x3d_mode": "cache"},
                    "tasks": tasks,
                }
            ]
            path = work / "play.yml"

            def run(*arguments):
                path.write_text(yaml.safe_dump(play))
                result = subprocess.run(
                    ["ansible-playbook", "-i", "localhost,", str(path), *arguments],
                    cwd=ROOT,
                    env={**os.environ, "ANSIBLE_LOCAL_TEMP": str(work / "tmp")},
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return result.stdout

            run("--check")
            self.assertTrue(
                all(path.read_text().strip() == "frequency" for path in controls)
            )
            run()
            self.assertTrue(
                all(path.read_text().strip() == "cache" for path in controls)
            )
            self.assertRegex(run(), r"changed=0\b")
            play[0]["vars"]["system_amd_x3d_mode"] = None
            self.assertRegex(run(), r"changed=0\b")
