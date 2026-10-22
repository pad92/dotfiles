"""Run package selection and unit deployment with isolated target state."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLES = ROOT / "ansible/roles"


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
class AnsibleRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def run_play(self, plays, inventory="localhost,", *arguments):
        playbook = self.directory / "play.yml"
        playbook.write_text(yaml.safe_dump(plays))
        result = subprocess.run(
            ["ansible-playbook", "-i", inventory, str(playbook), *arguments],
            cwd=ROOT,
            env={**os.environ, "ANSIBLE_LOCAL_TEMP": str(self.directory / "ansible")},
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_hyprlauncher_relaunch_detaches_from_ansible(self):
        handlers = yaml.safe_load((ROLES / "dotfiles/handlers/main.yml").read_text())
        handler = next(h for h in handlers if h["name"] == "Restart Hyprlauncher")
        binary = self.directory / "bin"
        binary.mkdir()
        # Simulate a running launcher which exits after SIGTERM.
        commands = {
            "pgrep": 'test ! -f "$STOP_MARKER"',
            "pkill": 'touch "$STOP_MARKER"',
            "uwsm": ('test "$*" = "app -t service -- hyprlauncher -d" || exit 42'),
        }
        for name, command in commands.items():
            path = binary / name
            path.write_text("#!/bin/sh\n" + command + "\n")
            path.chmod(0o755)
        result = subprocess.run(
            ["/bin/sh", "-c", handler["ansible.builtin.shell"]["cmd"]],
            env={
                **os.environ,
                "PATH": f"{binary}:{os.environ['PATH']}",
                "STOP_MARKER": str(self.directory / "stopped"),
            },
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_family_and_distribution_variables_produce_default_groups(self):
        selection = yaml.safe_load((ROLES / "packages/tasks/select.yml").read_text())
        default_task = next(
            task
            for task in selection
            if task["name"] == "Build default package group selection"
        )
        cases = [
            ("Archlinux", "Archlinux", "rolling", "rolling", None),
            ("Archlinux", "CachyOS", "rolling", "rolling", None),
            ("Debian", "Debian", "12.0", "12", "libgtk-3-0"),
            ("Debian", "Debian", "13.0", "13", "libgtk-3-0t64"),
            ("Debian", "Ubuntu", "22.04", "22", "libgtk-3-0"),
            ("Debian", "Ubuntu", "24.04", "24", "libgtk-3-0t64"),
            ("RedHat", "Fedora", "43", "43", None),
        ]
        plays = []
        for index, (family, distribution, version, major, gtk) in enumerate(cases):
            expected = ["01_base", "03_gtk"]
            if family == "Archlinux":
                expected += ["08_amd", "11_hyprland"]
            checks = ["packages_group_defaults == expected_groups"]
            if gtk:
                checks += ["packages_debian_gtk3_package == expected_gtk"]
            if family == "Archlinux":
                checks += [
                    (
                        "('cachyos-settings' in packages_family_groups.Archlinux['21_steam']) "
                        "== (ansible_facts.distribution == 'CachyOS')"
                    )
                ]
            plays.append(
                {
                    "hosts": f"case{index}",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "ansible_facts": {
                            "os_family": family,
                            "distribution": distribution,
                            "distribution_version": version,
                            "distribution_major_version": major,
                        },
                        "packages_detected_graphics_groups": (
                            ["08_amd"] if family == "Archlinux" else []
                        ),
                        "expected_groups": expected,
                        "expected_gtk": gtk,
                    },
                    "tasks": [
                        {
                            "ansible.builtin.include_role": {
                                "name": str(ROLES / "packages"),
                                "tasks_from": "load_platform_vars",
                                "public": True,
                            }
                        },
                        default_task,
                        {"ansible.builtin.assert": {"that": checks}},
                    ],
                }
            )
        self.run_play(plays, ",".join(f"case{i}" for i in range(len(cases))) + ",")

    def test_changed_units_use_try_restart_including_dropins(self):
        source = self.directory / "source/.config/systemd/user"
        source.mkdir(parents=True)
        for unit in [
            "awww.service",
            "awww_random.timer",
            "proton-pass-ssh-agent.service",
        ]:
            (source / unit).write_text("[Unit]\nDescription=Initial\n")
        for unit in ["mako.service", "hypridle.service"]:
            dropin = source / f"{unit}.d"
            dropin.mkdir()
            (dropin / "10-test.conf").write_text("[Service]\nEnvironment=TEST=before\n")
        (source / "default.target.wants").mkdir()
        links = {
            "pulseaudio.service": "/dev/null",
            "pipewire-session-manager.service": "/usr/lib/systemd/user/wireplumber.service",
            "default.target.wants/proton-pass-ssh-agent.service": "../proton-pass-ssh-agent.service",
            "default.target.wants/missing.service": "/nonexistent/dotfiles-test.service",
        }
        for name, destination in links.items():
            (source / name).symlink_to(destination)
        binary = self.directory / "bin"
        binary.mkdir()
        log = self.directory / "systemctl.jsonl"
        systemctl = binary / "systemctl"
        systemctl.write_text("""#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
args = sys.argv[1:]
with Path(os.environ['SYSTEMCTL_TEST_LOG']).open('a') as stream:
    stream.write(json.dumps(args) + '\\n')
if 'show' in args:
    active = 'inactive' if args[-1] == 'hypridle.service' else 'active'
    print(f'LoadState=loaded\\nActiveState={active}\\nCanReload=yes\\nNeedDaemonReload=no')
""")
        systemctl.chmod(0o755)
        plays = [
            {
                "hosts": "localhost",
                "connection": "local",
                "gather_facts": False,
                "environment": {
                    "PATH": f"{binary}:{os.environ['PATH']}",
                    "SYSTEMCTL_TEST_LOG": str(log),
                },
                "vars": {
                    "dotfiles_source_root": str(self.directory / "source"),
                    "dotfiles_home": str(self.directory / "target"),
                    "dotfiles_systemd_graphical_units": [],
                },
                "tasks": [
                    {
                        "ansible.builtin.include_role": {
                            "name": str(ROLES / "dotfiles"),
                            "tasks_from": "user_systemd",
                        }
                    }
                ],
            }
        ]
        initial = self.run_play(plays)
        self.assertNotIn('"atime":', initial.stdout)
        target = self.directory / "target/.config/systemd/user"
        for name, destination in links.items():
            self.assertTrue((target / name).is_symlink(), name)
            self.assertEqual(str((target / name).readlink()), destination)
        log.write_text("")
        (source / "awww_random.timer").write_text("[Unit]\nDescription=Updated\n")
        for unit in ["mako.service", "hypridle.service"]:
            (source / f"{unit}.d/10-test.conf").write_text(
                "[Service]\nEnvironment=TEST=after\n"
            )
        self.run_play(plays)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        actions = [args for args in calls if "show" not in args]
        self.assertEqual(actions[0], ["--user", "daemon-reload"])
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[1][:3], ["--user", "--no-block", "try-restart"])
        self.assertCountEqual(
            actions[1][3:],
            ["awww_random.timer", "mako.service", "hypridle.service"],
        )
        # Changing only an alias must reload the manager, without restarting units.
        log.write_text("")
        alias = "pipewire-session-manager.service"
        (source / alias).unlink()
        (source / alias).symlink_to("/nonexistent/alternate-session-manager.service")
        self.run_play(plays)
        self.assertEqual((target / alias).readlink(), (source / alias).readlink())
        self.assertEqual(
            [json.loads(line) for line in log.read_text().splitlines()],
            [["--user", "daemon-reload"]],
        )
        log.write_text("")
        result = self.run_play(plays)
        self.assertRegex(result.stdout, r"changed=0\b")
        self.assertEqual(log.read_text(), "")
        # A real file at a link destination must survive a failed deployment.
        mask = target / "pulseaudio.service"
        mask.unlink()
        mask.write_text("Existing local configuration\n")
        with self.assertRaisesRegex(AssertionError, "Refusing to replace"):
            self.run_play(plays)
        self.assertEqual(mask.read_text(), "Existing local configuration\n")
        self.assertEqual(log.read_text(), "")
