"""Run one Vault-driven user role (ssh, gpg) against a throwaway home directory."""

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from ansible_test_environment import PLAYBOOK_TIMEOUT, ansible_test_environment

ROOT = Path(__file__).resolve().parents[1]


def load_role(name: str) -> dict:
    """The role files the throwaway play is built from."""
    role = ROOT / "ansible/roles" / name
    handlers = role / "handlers/main.yml"
    return {
        "path": role,
        "defaults": yaml.safe_load((role / "defaults/main.yml").read_text()),
        "tasks": role / "tasks/main.yml",
        "handlers": yaml.safe_load(handlers.read_text()) if handlers.exists() else [],
    }


def site_entries(name: str) -> list[dict]:
    site = yaml.safe_load((ROOT / "ansible/site.yml").read_text())
    return [
        role
        for play in site
        for role in play.get("roles", [])
        if isinstance(role, dict) and role.get("role") == name
    ]


class RolePlayMixin:
    """setUp builds a home directory; run_play applies the role to it."""

    role: dict
    home_variable: str

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(
            prefix=f"{self.role['path'].name}-role-"
        )
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        # The play runs from the work directory, so templates resolve there.
        (self.work / "templates").symlink_to(self.role["path"] / "templates")
        self.home = self.work / "home"
        self.home.mkdir()

    def run_play(self, variables, succeed=True, extra=()):
        playbook = self.work / "play.yml"
        play = {
            "hosts": "localhost",
            "connection": "local",
            "gather_facts": False,
            "vars": {
                **self.role["defaults"],
                "ansible_python_interpreter": sys.executable,
                self.home_variable: str(self.home),
                **variables,
            },
            "tasks": yaml.safe_load(self.role["tasks"].read_text()),
        }
        if self.role["handlers"]:
            play["handlers"] = self.role["handlers"]
        playbook.write_text(yaml.safe_dump([play]))
        result = subprocess.run(
            ["ansible-playbook", "-i", "localhost,", *extra, str(playbook)],
            cwd=self.work,
            env=ansible_test_environment(self.work),
            capture_output=True,
            text=True,
            timeout=PLAYBOOK_TIMEOUT,
            check=False,
        )
        output = result.stdout + result.stderr
        if succeed:
            self.assertEqual(result.returncode, 0, output)
        else:
            self.assertNotEqual(result.returncode, 0, output)
        return output
