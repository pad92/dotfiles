"""Pinned RTK release installed by the agent_cli role."""

import hashlib
import io
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

import yaml
from ansible_test_environment import ansible_test_environment

ROOT = Path(__file__).resolve().parents[1]
VERSION = "9.9.9"
FAKE_RTK = f"#!/bin/sh\necho 'rtk {VERSION}'\n".encode()


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
class RtkInstallTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.home = self.work / "home"
        self.home.mkdir()
        self.archive = self.work / "rtk-test.tar.gz"
        self.write_archive(FAKE_RTK)

    def write_archive(self, content):
        with tarfile.open(self.archive, "w:gz") as tar:
            info = tarfile.TarInfo("rtk")
            info.size = len(content)
            info.mode = 0o755
            tar.addfile(info, io.BytesIO(content))
            license_info = tarfile.TarInfo("LICENSE")
            tar.addfile(license_info, io.BytesIO(b""))
        self.digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()

    def run_play(self, *, checksum=None, extra_vars=None):
        play = [
            {
                "hosts": "localhost",
                "connection": "local",
                "gather_facts": False,
                "vars": {
                    "agent_cli_home": str(self.home),
                    "agent_cli_rtk_version": VERSION,
                    "agent_cli_rtk_asset": self.archive.name,
                    "agent_cli_rtk_url": self.archive.as_uri(),
                    "agent_cli_rtk_checksum": checksum or f"sha256:{self.digest}",
                    **(extra_vars or {}),
                },
                "tasks": [
                    {
                        "ansible.builtin.import_role": {
                            "name": str(ROOT / "ansible/roles/agent_cli"),
                            "tasks_from": "rtk",
                        }
                    }
                ],
            }
        ]
        playbook = self.work / "play.yml"
        playbook.write_text(yaml.safe_dump(play))
        return subprocess.run(
            ["ansible-playbook", "-i", "localhost,", str(playbook)],
            env=ansible_test_environment(self.work),
            capture_output=True,
            text=True,
            check=False,
        )

    def test_installs_verified_binary_and_is_idempotent(self):
        first = self.run_play()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        binary = self.home / ".local/bin/rtk"
        self.assertEqual(binary.read_bytes(), FAKE_RTK)
        self.assertTrue(stat.S_IMODE(binary.stat().st_mode) & stat.S_IXUSR)
        second = self.run_play()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn("changed=0 ", second.stdout)

    def test_checksum_mismatch_installs_nothing(self):
        result = self.run_play(checksum="sha256:" + "0" * 64)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.home / ".local/bin/rtk").exists())

    def test_disabled_installs_nothing(self):
        result = self.run_play(extra_vars={"agent_cli_rtk_enabled": False})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.home / ".local/bin/rtk").exists())

    def test_download_directory_is_removed(self):
        self.run_play()
        leftovers = list(Path(tempfile.gettempdir()).glob("ansible.*rtk-*"))
        self.assertEqual(leftovers, [])
