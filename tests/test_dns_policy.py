"""Exercise the systemd-resolved migration against fake NetworkManager and Docker state."""

import importlib.util
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
TASKS = ROOT / "ansible/roles/system/tasks/dns.yml"
DEFAULTS = yaml.safe_load((ROOT / "ansible/roles/system/defaults/main.yml").read_text())
SPEC = importlib.util.spec_from_file_location(
    "dns_filters", ROOT / "ansible/filter_plugins/dns.py"
)
DNS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DNS)

# Profiles reported by the fake nmcli: UUID -> (ipv4.dns, ipv6.dns, connection.id).
PROFILES = {
    "home": ("127.0.0.1", "", "Home relay"),
    "both": ("127.0.0.1", "::1", "Both families"),
    "mixed": ("127.0.0.1,192.0.2.53", "", "Mixed servers"),
    "vpn": ("172.28.1.33,172.28.1.34", "", "Corporate VPN"),
    "auto": ("", "", "Plain DHCP"),
}
FAKE_NMCLI = """#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open(os.environ["FAKE_NMCLI_LOG"], "a") as log:
    log.write(json.dumps(args) + "\\n")
profiles = json.loads(os.environ["FAKE_NMCLI_PROFILES"])
if args == ["-g", "UUID", "connection", "show"]:
    print("\\n".join(profiles))
elif args[:3] == ["-g", "ipv4.dns,ipv6.dns,connection.id", "connection"]:
    print("\\n".join(profiles[args[4]]))
elif args[:3] == ["-t", "-f", "UUID,DEVICE"]:
    print("home:wlan0\\nvpn:tun0")
"""


class DnsFilterTests(unittest.TestCase):
    def profile_result(self, uuid, ipv4, ipv6, name):
        return {"item": uuid, "stdout": f"{ipv4}\n{ipv6}\n{name}"}

    def test_only_loopback_families_are_reset(self):
        migration = DNS.nm_loopback_dns_profiles(
            [self.profile_result(uuid, *values) for uuid, values in PROFILES.items()]
        )
        self.assertEqual(
            migration["reset"],
            [
                {
                    "uuid": "home",
                    "name": "Home relay",
                    "settings": ["ipv4.dns", "", "ipv4.ignore-auto-dns", "no"],
                },
                {
                    "uuid": "both",
                    "name": "Both families",
                    "settings": [
                        "ipv4.dns",
                        "",
                        "ipv4.ignore-auto-dns",
                        "no",
                        "ipv6.dns",
                        "",
                        "ipv6.ignore-auto-dns",
                        "no",
                    ],
                },
            ],
        )
        self.assertEqual(
            migration["mixed"], [{"uuid": "mixed", "name": "Mixed servers"}]
        )

    def test_annotated_servers_are_parsed_and_unknown_entries_kept(self):
        migration = DNS.nm_loopback_dns_profiles(
            [
                self.profile_result("sni", "127.0.0.1#dns.example", "", "Named"),
                self.profile_result("bracket", "", "[::1]#dns.example", "IPv6"),
                self.profile_result("odd", "not-an-address", "", "Odd"),
                self.profile_result("half", "127.0.0.1,not-an-address", "", "Half"),
            ]
        )
        self.assertEqual(
            [profile["uuid"] for profile in migration["reset"]], ["sni", "bracket"]
        )
        self.assertEqual([profile["uuid"] for profile in migration["mixed"]], ["half"])

    def test_profile_names_may_contain_separators(self):
        migration = DNS.nm_loopback_dns_profiles(
            [self.profile_result("home", "127.0.0.1", "", "Home: 5GHz, upstairs")]
        )
        self.assertEqual(migration["reset"][0]["name"], "Home: 5GHz, upstairs")

    def test_truncated_nmcli_output_fails(self):
        with self.assertRaises(DNS.AnsibleFilterError):
            DNS.nm_loopback_dns_profiles([{"item": "home", "stdout": "127.0.0.1"}])

    def test_docker_configuration_keeps_unrelated_keys(self):
        original = {
            "dns": ["192.0.2.1"],
            "default-address-pools": [{"base": "10.184.1.0/24", "size": 28}],
            "runtimes": {"nvidia": {"path": "nvidia-container-runtime"}},
        }
        merged = DNS.docker_daemon_dns(original, "10.184.1.1/28")
        self.assertEqual(original["dns"], ["192.0.2.1"])
        self.assertEqual(merged["bip"], "10.184.1.1/28")
        self.assertEqual(merged["dns"], ["10.184.1.1"])
        self.assertEqual(merged["runtimes"], original["runtimes"])
        self.assertEqual(
            merged["default-address-pools"], original["default-address-pools"]
        )

    def test_docker_bridge_must_be_an_ipv4_host_address(self):
        for invalid in ["10.184.1.0/28", "10.184.1.15/28", "fd00::1/64", "docker0"]:
            with (
                self.subTest(invalid=invalid),
                self.assertRaises(DNS.AnsibleFilterError),
            ):
                DNS.docker_bridge_address(invalid)
        with self.assertRaises(DNS.AnsibleFilterError):
            DNS.docker_daemon_dns(["not", "an", "object"], "10.184.1.1/28")


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
class DnsTaskTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.bin = self.work / "bin"
        self.bin.mkdir()
        nmcli = self.bin / "nmcli"
        nmcli.write_text(FAKE_NMCLI)
        nmcli.chmod(0o755)
        self.nmcli_log = self.work / "nmcli.log"
        self.nmcli_log.touch()
        self.tasks = yaml.safe_load(TASKS.read_text())

    def task_slice(self, first, last):
        names = [task["name"] for task in self.tasks]
        selected = yaml.safe_load(
            yaml.safe_dump(self.tasks[names.index(first) : names.index(last) + 1])
        )
        # Fixtures run unprivileged, so drop the root ownership of managed files.
        pending = list(selected)
        while pending:
            node = pending.pop()
            if isinstance(node, dict):
                node.pop("owner", None)
                node.pop("group", None)
                pending.extend(node.values())
            elif isinstance(node, list):
                pending.extend(node)
        return selected

    def run_play(self, tasks, variables, *arguments):
        playbook = self.work / "play.yml"
        playbook.write_text(
            yaml.safe_dump(
                [
                    {
                        "hosts": "localhost",
                        "connection": "local",
                        "gather_facts": False,
                        "vars": {**DEFAULTS, **variables},
                        "tasks": tasks,
                    }
                ]
            )
        )
        result = subprocess.run(
            ["ansible-playbook", "-i", "localhost,", str(playbook), *arguments],
            cwd=ROOT,
            env={
                **ansible_test_environment(self.work),
                "PATH": f"{self.bin}:{os.environ['PATH']}",
                "FAKE_NMCLI_LOG": str(self.nmcli_log),
                "FAKE_NMCLI_PROFILES": json.dumps(PROFILES),
            },
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def nmcli_calls(self):
        return [json.loads(line) for line in self.nmcli_log.read_text().splitlines()]

    def test_policy_renders_without_fallback_or_llmnr(self):
        for docker, listeners in [(True, ["10.184.1.1"]), (False, [])]:
            dropin = self.work / f"resolved-{docker}.conf"
            tasks = self.task_slice(
                "Validate the DNS policy", "Manage the systemd-resolved policy"
            )
            tasks[-1]["ansible.builtin.template"]["src"] = str(
                ROOT / "ansible/roles/system/templates/resolved-dns.conf.j2"
            )
            tasks[-1].pop("notify")
            self.run_play(
                tasks,
                {
                    "ansible_facts": {"hostname": "fixture"},
                    "packages_host_groups": {},
                    "packages_selected_groups": ["12_containers_docker"]
                    if docker
                    else [],
                    "system_dns_resolved_dropin": str(dropin),
                },
            )
            settings = [
                line
                for line in dropin.read_text().splitlines()
                if line and not line.startswith(("#", "["))
            ]
            with self.subTest(docker=docker):
                self.assertEqual(
                    settings,
                    ["LLMNR=no", "MulticastDNS=resolve", "FallbackDNS="]
                    + [f"DNSStubListenerExtra={address}" for address in listeners],
                )

    def test_unquoted_yaml_boolean_is_rejected(self):
        tasks = self.task_slice("Validate the DNS policy", "Validate the DNS policy")
        playbook = self.work / "play.yml"
        playbook.write_text(
            yaml.safe_dump(
                [
                    {
                        "hosts": "localhost",
                        "connection": "local",
                        "gather_facts": False,
                        "vars": {**DEFAULTS, "system_dns_llmnr": False},
                        "tasks": tasks,
                    }
                ]
            )
        )
        result = subprocess.run(
            ["ansible-playbook", "-i", "localhost,", str(playbook)],
            cwd=ROOT,
            env=ansible_test_environment(self.work),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("quoted strings", result.stdout)

    def test_loopback_profiles_are_reset_and_reapplied(self):
        tasks = self.task_slice(
            "List NetworkManager profiles", "Reapply DNS on active migrated profiles"
        )
        output = self.run_play(tasks, {})
        modifications = [call for call in self.nmcli_calls() if "modify" in call]
        self.assertEqual(
            modifications,
            [
                [
                    "connection",
                    "modify",
                    "home",
                    "ipv4.dns",
                    "",
                    "ipv4.ignore-auto-dns",
                    "no",
                ],
                [
                    "connection",
                    "modify",
                    "both",
                    "ipv4.dns",
                    "",
                    "ipv4.ignore-auto-dns",
                    "no",
                    "ipv6.dns",
                    "",
                    "ipv6.ignore-auto-dns",
                    "no",
                ],
            ],
        )
        reapplied = [call for call in self.nmcli_calls() if "reapply" in call]
        # Only the active migrated profile is reapplied; the VPN is untouched.
        self.assertEqual(reapplied, [["device", "reapply", "wlan0"]])
        self.assertIn("Mixed servers", output)

    def test_check_mode_reads_profiles_without_modifying_them(self):
        tasks = self.task_slice(
            "List NetworkManager profiles", "Reapply DNS on active migrated profiles"
        )
        self.run_play(tasks, {}, "--check")
        calls = self.nmcli_calls()
        self.assertTrue(calls)
        self.assertFalse(
            [call for call in calls if "modify" in call or "reapply" in call]
        )

    def test_legacy_files_are_backed_up_inert_then_removed(self):
        dispatcher = self.work / "dispatcher.d/90-dnsmasq-upstream"
        dispatcher.parent.mkdir()
        dispatcher.write_text("#!/bin/sh\necho relay\n")
        dispatcher.chmod(0o755)
        missing = self.work / "dnsmasq.d/home-failover.conf"
        backups = self.work / "backup"
        tasks = self.task_slice(
            "Check for files of the former DNS relay",
            "Check for files of the former DNS relay",
        ) + self.task_slice(
            "Create the DNS backup directory",
            "Remove files of the former DNS relay after backup",
        )
        tasks[-1].pop("notify")
        self.run_play(
            tasks,
            {
                "system_dns_legacy_files": [str(dispatcher), str(missing)],
                "system_dns_backup_dir": str(backups),
            },
        )
        self.assertFalse(dispatcher.exists())
        backup = backups / dispatcher.name
        self.assertEqual(backup.read_text(), "#!/bin/sh\necho relay\n")
        # A copy left executable could still be run if moved back by mistake.
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertEqual(backups.stat().st_mode & 0o777, 0o700)

    def test_docker_configuration_is_merged_once(self):
        daemon = self.work / "docker/daemon.json"
        daemon.parent.mkdir()
        original = {
            "dns": ["10.184.1.1"],
            "log-opts": {"max-size": "100m"},
            "runtimes": {"nvidia": {"args": [], "path": "nvidia-container-runtime"}},
        }
        daemon.write_text(json.dumps(original))
        block = self.task_slice(
            "Point Docker containers at the resolved bridge listener",
            "Point Docker containers at the resolved bridge listener",
        )
        block[0]["block"][-1].pop("notify")
        variables = {
            "system_dns_docker_selected": True,
            "system_docker_daemon_config_path": str(daemon),
        }
        self.run_play(block, variables)
        written = json.loads(daemon.read_text())
        self.assertEqual(written, {**original, "bip": "10.184.1.1/28"})
        self.assertRegex(self.run_play(block, variables), r"changed=0\b")


if __name__ == "__main__":
    unittest.main()
