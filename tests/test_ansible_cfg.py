"""Check the settings Ansible resolves from the repository ansible.cfg."""

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("ansible-config"), "requires ansible-config")
class BecomeConfigTests(unittest.TestCase):
    def become_exe(self, plugin: str) -> str:
        result = subprocess.run(
            ["ansible-config", "dump", "-t", "become", "--format", "json"],
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "ANSIBLE_CONFIG": str(ROOT / "ansible.cfg")},
        )
        for entry in json.loads(result.stdout):
            for option in entry.get(plugin, []):
                if option["name"] == "become_exe":
                    return option["value"]
        self.fail(f"Ansible reports no become_exe for {plugin}")

    def test_sudo_runs_with_a_dumb_terminal(self) -> None:
        # pam_systemd writes OSC 3008 sequences to the ssh -tt terminal
        # unless TERM is dumb, and the closing one follows the module JSON.
        self.assertEqual(self.become_exe("sudo"), "env TERM=dumb sudo")

    def test_other_become_methods_keep_their_executable(self) -> None:
        self.assertEqual(self.become_exe("su"), "su")


if __name__ == "__main__":
    unittest.main()
