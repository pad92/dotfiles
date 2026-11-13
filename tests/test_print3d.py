"""3D printing section: package group, site wiring and the F3D thumbnail setup."""

import getpass
import grp
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from ansible_test_environment import ansible_test_environment

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "ansible/site.yml"
COLLECTIONS = ROOT / ".ansible/collections"
ARCH_GROUPS = yaml.safe_load(
    (ROOT / "ansible/roles/packages/vars/archlinux.yml").read_text()
)["packages_family_groups"]["Archlinux"]
WORKSTATION = yaml.safe_load(
    (ROOT / "ansible/group_vars/all/packages.yml").read_text()
)["packages_workstation_groups"]
EGL_CONFIG = [{"options": {"rendering-backend": "egl"}}]
CLEARED = ["fail", "normal", "large", "x-large", "xx-large"]


class Print3dWiringTests(unittest.TestCase):
    def test_group_installs_the_slicer_and_the_thumbnailer(self):
        self.assertEqual(ARCH_GROUPS["24_3dprint"], ["f3d", "prusa-slicer"])
        self.assertIn("24_3dprint", WORKSTATION)

    def test_role_runs_under_the_3dprint_tag_for_the_selected_group(self):
        entry = next(
            role
            for role in yaml.safe_load(SITE.read_text())[0]["roles"]
            if role["role"] == "print3d"
        )
        self.assertEqual(entry["tags"], ["3dprint"])
        self.assertIn("'24_3dprint' in", entry["when"][-1])
        self.assertIn("!= 'plan'", entry["when"][0])


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
@unittest.skipUnless(COLLECTIONS.is_dir(), "requires pinned Ansible collections")
class Print3dRoleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.config_dir = self.work / "etc/f3d"
        self.cache = self.work / "cache/thumbnails"
        self.environment = ansible_test_environment(self.work)
        self.environment["ANSIBLE_ROLES_PATH"] = str(ROOT / "ansible/roles")
        self.environment["ANSIBLE_COLLECTIONS_PATH"] = str(COLLECTIONS)

    def run_role(self, options):
        playbook = self.work / "play.yml"
        playbook.write_text(
            yaml.safe_dump(
                [
                    {
                        "hosts": "localhost",
                        "connection": "local",
                        "gather_facts": False,
                        "vars": {
                            "print3d_packages": [],
                            "print3d_f3d_config_dir": str(self.config_dir),
                            "print3d_f3d_config_owner": getpass.getuser(),
                            "print3d_f3d_config_group": grp.getgrgid(
                                os.getgid()
                            ).gr_name,
                            "print3d_f3d_thumbnail_options": options,
                            "print3d_thumbnail_cache_dir": str(self.cache),
                        },
                        "pre_tasks": [
                            {
                                "name": "Provide isolated facts",
                                "ansible.builtin.set_fact": {
                                    "ansible_facts": {"os_family": "Archlinux"}
                                },
                            }
                        ],
                        "roles": ["print3d"],
                    }
                ]
            )
        )
        result = subprocess.run(
            ["ansible-playbook", "-i", "localhost,", str(playbook)],
            cwd=self.work,
            env=self.environment,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def seed_cache(self):
        for name in [*CLEARED, "kept"]:
            (self.cache / name).mkdir(parents=True, exist_ok=True)
            (self.cache / name / "thumb.png").write_bytes(b"png")

    def test_config_change_clears_the_cache_once(self):
        self.seed_cache()
        output = self.run_role({"rendering-backend": "egl"})
        config = self.config_dir / "thumbnail.json"
        self.assertEqual(json.loads(config.read_text()), EGL_CONFIG)
        self.assertTrue(config.read_text().endswith("]\n"))
        self.assertEqual(config.stat().st_mode & 0o777, 0o644)
        self.assertEqual(self.config_dir.stat().st_mode & 0o777, 0o755)
        self.assertIn("RUNNING HANDLER [print3d : Clear the GNOME thumbnail", output)
        for name in CLEARED:
            self.assertFalse((self.cache / name).exists(), name)
        self.assertTrue((self.cache / "kept/thumb.png").exists())

        # Unchanged configuration: nothing changes and new previews stay.
        self.seed_cache()
        output = self.run_role({"rendering-backend": "egl"})
        self.assertIn("changed=0", output)
        self.assertNotIn("RUNNING HANDLER", output)
        for name in CLEARED:
            self.assertTrue((self.cache / name / "thumb.png").exists(), name)

        output = self.run_role({"rendering-backend": "egl", "verbose": "quiet"})
        self.assertIn("RUNNING HANDLER [print3d : Clear the GNOME thumbnail", output)
        self.assertFalse((self.cache / "fail").exists())

    def test_existing_identical_config_is_left_alone(self):
        self.config_dir.mkdir(parents=True)
        (self.config_dir / "thumbnail.json").write_text(
            json.dumps(EGL_CONFIG, indent=2) + "\n"
        )
        (self.config_dir / "thumbnail.json").chmod(0o644)
        self.config_dir.chmod(0o755)
        self.seed_cache()
        output = self.run_role({"rendering-backend": "egl"})
        self.assertIn("changed=0", output)
        self.assertTrue((self.cache / "fail/thumb.png").exists())


if __name__ == "__main__":
    unittest.main()
