"""Exercise the systemd-resolved migration against fake NetworkManager and Docker state."""

import base64
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml
from ansible_test_environment import ansible_test_environment

ROOT = Path(__file__).resolve().parents[1]
DETECTION = ROOT / "ansible/roles/system/tasks/dns.yml"
TASKS = ROOT / "ansible/roles/system/tasks/dns_policy.yml"
DEFAULTS = yaml.safe_load((ROOT / "ansible/roles/system/defaults/main.yml").read_text())
SPEC = importlib.util.spec_from_file_location(
    "dns_filters", ROOT / "ansible/filter_plugins/dns.py"
)
DNS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DNS)


def profile(name, kind, ipv4=None, ipv6=None):
    """Build a fake profile; ipv4/ipv6 are (dns, method), None when absent."""
    properties = {"connection.id": name, "connection.type": kind}
    for family, setting in [("ipv4", ipv4), ("ipv6", ipv6)]:
        if setting is not None:
            properties[f"{family}.dns"], properties[f"{family}.method"] = setting
    return properties


# Profiles reported by the fake nmcli, by UUID.
PROFILES = {
    "home": profile(
        "Home relay", "802-11-wireless", ("127.0.0.1", "auto"), ("", "auto")
    ),
    "both": profile(
        "Both families", "802-11-wireless", ("127.0.0.1", "auto"), ("::1", "auto")
    ),
    "v6": profile("IPv6 relay", "802-3-ethernet", ("", "disabled"), ("::1", "dhcp")),
    "mixed": profile(
        "Mixed servers", "802-3-ethernet", ("127.0.0.1,192.0.2.53", "auto")
    ),
    "static": profile(
        "Office static", "802-3-ethernet", ("127.0.0.1", "manual"), ("", "ignore")
    ),
    "vpn": profile("Corporate VPN", "vpn", ("192.0.2.53,192.0.2.54", "auto")),
    "vpnrelay": profile("Relay VPN", "vpn", ("127.0.0.1", "auto")),
    "auto": profile("Plain DHCP", "802-3-ethernet", ("", "auto"), ("", "auto")),
    # A bridge port has no ipv4 or ipv6 setting at all.
    "port": profile("Bridge port", "802-3-ethernet"),
}
IPV4_RESET = ["ipv4.dns", "", "ipv4.ignore-auto-dns", "no"]
IPV6_RESET = ["ipv6.dns", "", "ipv6.ignore-auto-dns", "no"]
# Active connections: (UUID, DEVICE).
ACTIVE = [("home", "wlan0"), ("vpn", "tun0")]
# Mimics nmcli 1.58, checked against the real client:
# - -g prints one value per line, escapes ':' and backslash unless -e no is
#   given, and prints nothing for a setting the profile lacks;
# - -t -f on one profile prints property:value lines, unescaped, and skips the
#   settings the profile lacks;
# - -t -f on a listing escapes ':' and backslash unless -e no is given.
# Unknown calls fail, so an unexpected command fails the play. Reapply fails
# on tun devices to model a device NetworkManager cannot reapply in place.
FAKE_NMCLI = r"""#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open(os.environ["FAKE_NMCLI_LOG"], "a") as log:
    log.write(json.dumps(args) + "\n")
profiles = json.loads(os.environ["FAKE_NMCLI_PROFILES"])
active = json.loads(os.environ["FAKE_NMCLI_ACTIVE"])
escape, values_only, terse, fields = True, False, False, None
while args and args[0].startswith("-"):
    option = args.pop(0)
    if option == "--version":
        print("nmcli tool, version 1.58.1")
        sys.exit(0)
    if option == "-e":
        escape = args.pop(0) == "yes"
    elif option == "-g":
        values_only, terse, fields = True, True, args.pop(0).split(",")
    elif option == "-t":
        terse = True
    elif option == "-f":
        fields = args.pop(0).split(",")
    else:
        sys.exit(f"fake nmcli: unsupported option {option}")

def show(value):
    if terse and escape:
        return value.replace("\\", "\\\\").replace(":", "\\:")
    return value

if args == ["connection", "show"] and fields == ["UUID"]:
    print("\n".join(profiles))
elif args[:2] == ["connection", "show"] and args[2:] == ["--active"]:
    for uuid, device in active:
        values = {
            "UUID": uuid,
            "TYPE": profiles[uuid]["connection.type"],
            "DEVICE": device,
        }
        print(":".join(show(values[field]) for field in fields))
elif args[:2] == ["connection", "show"] and len(args) == 3:
    properties = profiles[args[2]]
    for field in fields:
        if field not in properties:
            continue
        if values_only:
            print(show(properties[field]))
        else:
            print(f"{field}:{properties[field]}")
elif args[:2] == ["connection", "modify"]:
    pass
elif args[:2] == ["device", "reapply"] and len(args) == 3:
    if args[2].startswith("tun"):
        sys.exit("Error: Reapplying connection to device '%s' failed" % args[2])
else:
    sys.exit(f"fake nmcli: unsupported command {args}")
"""
FAKE_SS = """#!/bin/sh
[ "$*" = "-Hlntup sport = :53" ] || { echo "fake ss: unexpected $*" >&2; exit 2; }
printf '%s' "$FAKE_SS_OUTPUT"
"""
FAKE_RESOLVECTL = """#!/bin/sh
[ "$*" = "query --legend=no localhost" ] || { echo "unexpected $*" >&2; exit 2; }
[ "${FAKE_RESOLVECTL_RC:-0}" = 0 ] || { echo "Failed to resolve" >&2; exit 1; }
echo "localhost: 127.0.0.1"
"""
# ss -Hlntup lines as systemd-resolved, libvirt and a wildcard dnsmasq show them.
SS_RESOLVED = (
    'udp UNCONN 0 0 127.0.0.53%lo:53 0.0.0.0:* users:(("systemd-resolve",pid=7,fd=19))\n'
    'tcp LISTEN 0 4096 10.184.1.1:53 0.0.0.0:* users:(("systemd-resolve",pid=7,fd=22))\n'
    'udp UNCONN 0 0 192.168.122.1:53 0.0.0.0:* users:(("dnsmasq",pid=9,fd=5))\n'
)
SS_WILDCARD_DNSMASQ = (
    'udp UNCONN 0 0 0.0.0.0:53 0.0.0.0:* users:(("dnsmasq",pid=11,fd=4))\n'
    'tcp LISTEN 0 32 [::]:53 [::]:* users:(("dnsmasq",pid=11,fd=7))\n'
)
SS_BRIDGE_UNBOUND = (
    'udp UNCONN 0 0 10.184.1.1:53 0.0.0.0:* users:(("unbound",pid=12,fd=3))\n'
)
# service_facts entries of a host the policy applies to.
RUNNING_SERVICES = {
    "systemd-resolved.service": {"state": "stopped"},
    "NetworkManager.service": {"state": "running"},
}
OLD_GUIDE_RC_MANAGER = "[main]\nrc-manager=resolvconf\n"
# Headers written by the programs that own a regular resolv.conf.
STUB_HEADER = (
    "# This is /run/systemd/resolve/stub-resolv.conf managed by "
    "man:systemd-resolved(8).\n# Do not edit.\n"
)
UPLINK_HEADER = (
    "# This is /run/systemd/resolve/resolv.conf managed by "
    "man:systemd-resolved(8).\n# Do not edit.\n"
)
VPN_HEADER = (
    "# Dynamic resolv.conf(5) file for glibc resolver(3) generated by forticlient\n"
)


def keyed(properties):
    return "\n".join(
        f"{key}:{properties[key]}"
        for key in [
            "ipv4.dns",
            "ipv6.dns",
            "ipv4.method",
            "ipv6.method",
            "connection.id",
        ]
        if key in properties
    )


def b64(text):
    return base64.b64encode(text.encode()).decode()


class DnsFilterTests(unittest.TestCase):
    def migration(self, profiles=None):
        profiles = PROFILES if profiles is None else profiles
        return DNS.nm_loopback_dns_profiles(
            [{"item": uuid, "stdout": keyed(props)} for uuid, props in profiles.items()]
        )

    def test_only_automatic_loopback_families_are_reset(self):
        migration = self.migration()
        self.assertEqual(
            migration["reset"],
            [
                {"uuid": "home", "name": "Home relay", "settings": IPV4_RESET},
                {
                    "uuid": "both",
                    "name": "Both families",
                    "settings": IPV4_RESET + IPV6_RESET,
                },
                {"uuid": "v6", "name": "IPv6 relay", "settings": IPV6_RESET},
                {"uuid": "vpnrelay", "name": "Relay VPN", "settings": IPV4_RESET},
            ],
        )
        self.assertEqual(
            migration["mixed"], [{"uuid": "mixed", "name": "Mixed servers"}]
        )

    def test_static_loopback_families_are_reported_not_reset(self):
        migration = self.migration(
            {
                "static": PROFILES["static"],
                "linklocal": profile(
                    "Link local", "802-3-ethernet", ("127.0.0.1", "link-local")
                ),
                "split": profile(
                    "Split", "802-3-ethernet", ("127.0.0.1", "auto"), ("::1", "manual")
                ),
            }
        )
        self.assertEqual(
            migration["static"],
            [
                {
                    "uuid": "static",
                    "name": "Office static",
                    "family": "ipv4",
                    "method": "manual",
                },
                {
                    "uuid": "linklocal",
                    "name": "Link local",
                    "family": "ipv4",
                    "method": "link-local",
                },
                {
                    "uuid": "split",
                    "name": "Split",
                    "family": "ipv6",
                    "method": "manual",
                },
            ],
        )
        # The automatic family of a split profile is still reset.
        self.assertEqual(
            migration["reset"],
            [{"uuid": "split", "name": "Split", "settings": IPV4_RESET}],
        )

    def test_profiles_without_ip_settings_are_ignored(self):
        migration = self.migration({"port": PROFILES["port"]})
        self.assertEqual(migration, {"reset": [], "mixed": [], "static": []})

    def test_annotated_servers_are_parsed_and_unknown_entries_kept(self):
        migration = self.migration(
            {
                "sni": profile("Named", "x", ("127.0.0.1#dns.example", "auto")),
                "bracket": profile("IPv6", "x", None, ("[::1]#dns.example", "auto")),
                "odd": profile("Odd", "x", ("not-an-address", "auto")),
                "half": profile("Half", "x", ("127.0.0.1,not-an-address", "auto")),
            }
        )
        self.assertEqual(
            [profile["uuid"] for profile in migration["reset"]], ["sni", "bracket"]
        )
        self.assertEqual([profile["uuid"] for profile in migration["mixed"]], ["half"])

    def test_profile_names_may_contain_separators(self):
        migration = self.migration(
            {"home": profile("Home: 5GHz, upstairs", "x", ("127.0.0.1", "auto"))}
        )
        self.assertEqual(migration["reset"][0]["name"], "Home: 5GHz, upstairs")

    def test_unnamed_profiles_fall_back_to_their_uuid(self):
        migration = DNS.nm_loopback_dns_profiles(
            [{"item": "u1", "stdout": "ipv4.dns:127.0.0.1\nipv4.method:auto"}]
        )
        self.assertEqual(migration["reset"][0]["name"], "u1")

    def test_malformed_nmcli_output_fails(self):
        with self.assertRaises(DNS.AnsibleFilterError):
            DNS.nm_loopback_dns_profiles([{"item": "home", "stdout": "127.0.0.1"}])

    def test_dnsmasq_upstream_servers_are_listed_once(self):
        servers = DNS.dnsmasq_upstream_servers(
            [
                "# relay\nserver=192.0.2.1\nno-resolv\n server = 192.0.2.2 \n",
                "server=/corp.example/10.0.0.53\nserver=192.0.2.1\nlisten-address=127.0.0.1\n",
            ]
        )
        self.assertEqual(servers, ["192.0.2.1", "192.0.2.2", "/corp.example/10.0.0.53"])

    def test_legacy_networkmanager_files_are_removed_only_when_dns_mode_only(self):
        results = [
            {"item": {"stat": {"path": path}}, "content": b64(content)}
            for path, content in [
                ("/a/rc-manager.conf", OLD_GUIDE_RC_MANAGER),
                ("/a/dns.conf", "# relay\n[main]\ndns=none\nrc-manager=unmanaged\n"),
                ("/b/dns.conf", "[main]\ndns=none\n[logging]\nlevel=DEBUG\n"),
                (
                    "/c/rc-manager.conf",
                    "[main]\nrc-manager=resolvconf\nplugins=keyfile\n",
                ),
                ("/d/dns.conf", "# empty\n"),
            ]
        ]
        self.assertEqual(
            DNS.nm_legacy_dns_files(results),
            {
                "remove": ["/a/rc-manager.conf", "/a/dns.conf"],
                "keep": ["/b/dns.conf", "/c/rc-manager.conf", "/d/dns.conf"],
            },
        )

    def test_resolv_conf_origin(self):
        cases = [
            ("# Generated by resolvconf\nnameserver 192.0.2.1\n", True, "openresolv"),
            (
                "# Generated by NetworkManager\nnameserver 192.0.2.1\n",
                True,
                "NetworkManager",
            ),
            (
                STUB_HEADER + "nameserver 127.0.0.53\noptions edns0 trust-ad\n",
                True,
                "a copy of the systemd-resolved stub file",
            ),
            (
                UPLINK_HEADER + "nameserver 192.0.2.1\n",
                True,
                "a copy of the systemd-resolved uplink file",
            ),
            ("nameserver 127.0.0.1\nnameserver ::1\n", True, "loopback name servers"),
            ("nameserver 127.0.0.53\n", True, "loopback name servers"),
            (
                VPN_HEADER + "nameserver 192.0.2.10\nsearch corp.example\n",
                False,
                VPN_HEADER[2:].strip(),
            ),
            ("nameserver 192.0.2.1\n", False, "unknown writer"),
            ("", False, "unknown writer"),
        ]
        for content, managed, origin in cases:
            with self.subTest(content=content):
                self.assertEqual(
                    DNS.resolv_conf_origin(content),
                    {"managed": managed, "origin": origin},
                )

    def test_port_conflicts_name_foreign_wildcard_and_bridge_listeners(self):
        self.assertEqual(DNS.dns_port_conflicts(SS_RESOLVED, "10.184.1.1"), [])
        self.assertEqual(
            DNS.dns_port_conflicts(SS_WILDCARD_DNSMASQ, "10.184.1.1"),
            ["udp 0.0.0.0:53 (dnsmasq)", "tcp [::]:53 (dnsmasq)"],
        )
        self.assertEqual(
            DNS.dns_port_conflicts(SS_WILDCARD_DNSMASQ, "10.184.1.1", ["dnsmasq"]), []
        )
        self.assertEqual(
            DNS.dns_port_conflicts(SS_BRIDGE_UNBOUND, "10.184.1.1"),
            ["udp 10.184.1.1:53 (unbound)"],
        )
        # Without process details a wildcard still conflicts; a bridge
        # listener is taken to be resolved from an earlier run.
        self.assertEqual(
            DNS.dns_port_conflicts(
                "udp UNCONN 0 0 *:53 *:*\nudp UNCONN 0 0 10.184.1.1:53 0.0.0.0:*\n",
                "10.184.1.1",
            ),
            ["udp *:53 (unknown process)"],
        )

    def test_reapply_targets_skip_connections_that_need_a_reconnect(self):
        reset = [
            {"uuid": uuid, "name": name, "settings": []}
            for uuid, name in [
                ("home", "Home"),
                ("vpn", "Office VPN"),
                ("wg", "WireGuard"),
                ("tun", "Tunnel"),
            ]
        ]
        active = (
            "home:802-11-wireless:wlan0\n"
            "vpn:vpn:wlan0\n"
            "wg:wireguard:wg0\n"
            "tun:tun:tun0\n"
            "other:802-3-ethernet:eth0\n"
        )
        targets = DNS.nm_reapply_targets(active, reset)
        self.assertEqual(targets["devices"], ["wlan0"])
        self.assertEqual(targets["reconnect"], ["Office VPN", "WireGuard", "Tunnel"])

    def test_reapply_targets_unescape_terse_fields(self):
        reset = [{"uuid": "esc", "name": "Escaped", "settings": []}]
        targets = DNS.nm_reapply_targets(r"esc:802-3-ethernet:odd\:na\\me", reset)
        self.assertEqual(targets["devices"], ["odd:na\\me"])
        with self.assertRaises(DNS.AnsibleFilterError):
            DNS.nm_reapply_targets("esc:802-3-ethernet", reset)

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

    def test_fixed_cidr_inside_the_bridge_is_kept(self):
        for fixed_cidr in ["10.184.1.0/28", "10.184.1.8/29"]:
            with self.subTest(fixed_cidr=fixed_cidr):
                merged = DNS.docker_daemon_dns(
                    {"bip": "172.17.0.1/16", "fixed-cidr": fixed_cidr},
                    "10.184.1.1/28",
                )
                self.assertEqual(merged["fixed-cidr"], fixed_cidr)

    def test_fixed_cidr_outside_the_bridge_fails(self):
        # The default Docker bridge range, kept from before bip was pinned.
        for fixed_cidr in ["172.17.5.0/24", "10.184.1.0/24", "not-a-network", 17]:
            with (
                self.subTest(fixed_cidr=fixed_cidr),
                self.assertRaisesRegex(DNS.AnsibleFilterError, "fixed-cidr"),
            ):
                DNS.docker_daemon_dns(
                    {"bip": "172.17.0.1/16", "fixed-cidr": fixed_cidr},
                    "10.184.1.1/28",
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


def task_names(path):
    return [task["name"] for task in yaml.safe_load(path.read_text())]


class DnsTaskOrderTests(unittest.TestCase):
    # A migrated host resolves through dnsmasq and a regular resolv.conf until
    # resolved takes over; any other order leaves it without DNS for a while.
    def test_resolved_runs_before_dnsmasq_stops_and_resolv_conf_switches(self):
        names = task_names(TASKS)
        order = [
            "Require the Docker bridge address to be free for resolved",
            "Manage the systemd-resolved policy",
            "Enable and start systemd-resolved",
            "Move NetworkManager profiles off the loopback relay",
            "Remove files of the former DNS setup after backup",
            "Stop and disable the standalone dnsmasq relay",
            "Apply the resolver changes before switching resolv.conf",
            "Require the systemd-resolved stub file",
            "Point resolv.conf at the systemd-resolved stub",
            "Require systemd-resolved to answer queries",
        ]
        positions = [names.index(name) for name in order]
        self.assertEqual(positions, sorted(positions))
        tasks = {task["name"]: task for task in yaml.safe_load(TASKS.read_text())}
        resolved = tasks["Enable and start systemd-resolved"][
            "ansible.builtin.systemd_service"
        ]
        self.assertEqual((resolved["enabled"], resolved["state"]), (True, "started"))
        flush = tasks["Apply the resolver changes before switching resolv.conf"]
        self.assertEqual(flush["ansible.builtin.meta"], "flush_handlers")

    # The port check must fail before the first change to the host.
    def test_only_reads_happen_before_the_port_check(self):
        names = task_names(TASKS)
        tasks = yaml.safe_load(TASKS.read_text())
        before = tasks[
            : names.index("Require the Docker bridge address to be free for resolved")
        ]
        read_only = {
            "ansible.builtin.assert",
            "ansible.builtin.set_fact",
            "ansible.builtin.stat",
            "ansible.builtin.slurp",
            "ansible.builtin.debug",
            "ansible.builtin.command",
        }
        for task in before:
            with self.subTest(task=task["name"]):
                self.assertTrue(read_only & task.keys())
                if "ansible.builtin.command" in task:
                    self.assertIs(task["changed_when"], False)


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
class DnsTaskTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.bin = self.work / "bin"
        self.bin.mkdir()
        for name, script in [
            ("nmcli", FAKE_NMCLI),
            ("ss", FAKE_SS),
            ("resolvectl", FAKE_RESOLVECTL),
        ]:
            fake = self.bin / name
            fake.write_text(script)
            fake.chmod(0o755)
        self.nmcli_log = self.work / "nmcli.log"
        self.nmcli_log.touch()
        self.active = ACTIVE
        self.environment = {"FAKE_SS_OUTPUT": "", "FAKE_RESOLVECTL_RC": "0"}
        self.path = f"{self.bin}:{os.environ['PATH']}"
        self.relay_file = self.work / "dnsmasq.d/home-failover.conf"

    def task_slice(self, first, last, source=TASKS):
        tasks = yaml.safe_load(source.read_text())
        names = [task["name"] for task in tasks]
        selected = tasks[names.index(first) : names.index(last) + 1]
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

    def run_play(self, tasks, variables, *arguments, succeed=True):
        playbook = self.work / "play.yml"
        playbook.write_text(
            yaml.safe_dump(
                [
                    {
                        "hosts": "localhost",
                        "connection": "local",
                        "gather_facts": False,
                        "vars": {
                            **DEFAULTS,
                            "ansible_python_interpreter": sys.executable,
                            **variables,
                        },
                        "tasks": tasks,
                    }
                ]
            )
        )
        result = subprocess.run(
            [
                shutil.which("ansible-playbook"),
                "-i",
                "localhost,",
                str(playbook),
                *arguments,
            ],
            cwd=ROOT,
            env={
                **ansible_test_environment(self.work),
                **self.environment,
                "PATH": self.path,
                "FAKE_NMCLI_LOG": str(self.nmcli_log),
                "FAKE_NMCLI_PROFILES": json.dumps(PROFILES),
                "FAKE_NMCLI_ACTIVE": json.dumps(self.active),
            },
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if succeed:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result.stdout

    def nmcli_calls(self):
        return [json.loads(line) for line in self.nmcli_log.read_text().splitlines()]

    def modified_profiles(self):
        return {
            call[2]: call[3:]
            for call in self.nmcli_calls()
            if call[:2] == ["connection", "modify"]
        }

    def write(self, path, content, mode=0o644):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        path.chmod(mode)
        return path

    def detection_slice(self):
        return self.task_slice(
            "Find the standalone dnsmasq unit",
            "Report legacy NetworkManager settings left in place",
        )

    def run_profile_migration(self, relay_present, *arguments, legacy_files=()):
        if relay_present:
            self.write(self.relay_file, "server=192.0.2.1\nserver=192.0.2.2\n")
        tasks = self.detection_slice() + self.task_slice(
            "Move NetworkManager profiles off the loopback relay",
            "Move NetworkManager profiles off the loopback relay",
        )
        return self.run_play(
            tasks,
            {
                "system_dns_relay_files": [str(self.relay_file)],
                "system_dns_legacy_files": [str(path) for path in legacy_files],
            },
            *arguments,
        )

    def test_policy_renders_without_fallback_or_llmnr(self):
        for docker, listeners in [(True, ["10.184.1.1"]), (False, [])]:
            dropin = self.work / f"resolved-{docker}.conf"
            tasks = self.task_slice(
                "Validate the DNS policy",
                "Add the Docker bridge to the resolved stub listeners",
            ) + self.task_slice(
                "Create the systemd-resolved drop-in directory",
                "Manage the systemd-resolved policy",
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
        output = self.run_play(tasks, {"system_dns_llmnr": False}, succeed=False)
        self.assertIn("quoted strings", output)

    def test_loopback_profiles_are_reset_and_reapplied_when_the_relay_is_found(self):
        output = self.run_profile_migration(relay_present=True)
        self.assertEqual(
            self.modified_profiles(),
            {
                "home": IPV4_RESET,
                "both": IPV4_RESET + IPV6_RESET,
                "v6": IPV6_RESET,
                "vpnrelay": IPV4_RESET,
            },
        )
        reapplied = [call for call in self.nmcli_calls() if "reapply" in call]
        # Only the active migrated profile is reapplied; the VPN is untouched.
        self.assertEqual(reapplied, [["device", "reapply", "wlan0"]])
        self.assertIn("Mixed servers", output)

    # A static profile has no DHCP DNS to fall back on once its server is gone.
    def test_static_profiles_are_reported_with_the_relay_servers(self):
        output = self.run_profile_migration(relay_present=True)
        self.assertNotIn("static", self.modified_profiles())
        self.assertIn("Office static", output)
        self.assertIn("192.0.2.1, 192.0.2.2", output)

    # Real nmcli prints no line for a setting the profile lacks.
    def test_port_profiles_without_ip_settings_do_not_stop_the_play(self):
        self.run_profile_migration(relay_present=True)
        self.assertNotIn("port", self.modified_profiles())
        self.assertIn(
            ["connection", "show", "port"],
            [call[-3:] for call in self.nmcli_calls()],
        )

    # nmcli -g prints ::1 as \:\:1 unless escaping is turned off.
    def test_ipv6_loopback_servers_are_reset_despite_terse_escaping(self):
        self.run_profile_migration(relay_present=True)
        modified = self.modified_profiles()
        self.assertEqual(modified["v6"], IPV6_RESET)
        self.assertIn("ipv6.dns", modified["both"])

    def test_vpn_connections_are_reported_instead_of_reapplied(self):
        self.active = [("home", "wlan0"), ("vpnrelay", "tun1")]
        output = self.run_profile_migration(relay_present=True)
        reapplied = [call for call in self.nmcli_calls() if "reapply" in call]
        self.assertEqual(reapplied, [["device", "reapply", "wlan0"]])
        self.assertIn("Reconnect these connections", output)
        self.assertIn("Relay VPN", output)

    def test_loopback_profiles_are_untouched_without_the_relay(self):
        # rc-manager.conf alone comes from the install guide, not from the relay.
        rc_manager = self.write(
            self.work / "conf.d/rc-manager.conf", OLD_GUIDE_RC_MANAGER
        )
        self.run_profile_migration(relay_present=False, legacy_files=[rc_manager])
        self.assertEqual(self.nmcli_calls(), [])

    def test_check_mode_reads_profiles_without_modifying_them(self):
        self.run_profile_migration(True, "--check")
        calls = self.nmcli_calls()
        self.assertTrue(calls)
        self.assertFalse(
            [call for call in calls if "modify" in call or "reapply" in call]
        )

    def leftover_play(self, relay_files, legacy_files, *arguments):
        tasks = self.detection_slice() + self.task_slice(
            "Create the DNS backup directories",
            "Remove files of the former DNS setup after backup",
        )
        tasks[-1].pop("notify")
        return self.run_play(
            tasks,
            {
                "system_dns_relay_files": [str(path) for path in relay_files],
                "system_dns_legacy_files": [str(path) for path in legacy_files],
                "system_dns_backup_dir": str(self.work / "backup"),
            },
            *arguments,
        )

    def test_leftovers_are_backed_up_by_full_path_then_removed(self):
        first = self.write(
            self.work / "dispatcher.d/90-dnsmasq-upstream",
            "#!/bin/sh\necho relay\n",
            0o755,
        )
        second = self.write(
            self.work / "other/90-dnsmasq-upstream", "#!/bin/sh\necho other\n", 0o755
        )
        legacy = self.write(self.work / "conf.d/rc-manager.conf", OLD_GUIDE_RC_MANAGER)
        missing = self.work / "dnsmasq.d/home-failover.conf"
        contents = {path: path.read_text() for path in [first, second, legacy]}
        self.leftover_play([first, second, missing], [legacy])
        backups = self.work / "backup"
        for path, content in contents.items():
            with self.subTest(path=path):
                self.assertFalse(path.exists())
                backup = Path(f"{backups}{path}")
                self.assertEqual(backup.read_text(), content)
                # A copy left executable could still be run if moved back by mistake.
                self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertFalse(Path(f"{backups}{missing}").exists())
        self.assertEqual(backups.stat().st_mode & 0o777, 0o700)

    def test_legacy_settings_with_other_content_are_kept_and_reported(self):
        own = self.write(
            self.work / "conf.d/dns.conf", "[main]\ndns=none\n[logging]\nlevel=DEBUG\n"
        )
        output = self.leftover_play([], [own])
        self.assertEqual(own.read_text(), "[main]\ndns=none\n[logging]\nlevel=DEBUG\n")
        self.assertIn("set more than the DNS mode", output)
        self.assertIn(str(own), output)

    def test_check_mode_completes_on_a_first_migration(self):
        relay = self.write(self.relay_file, "server=192.0.2.1\n")
        legacy = self.write(self.work / "conf.d/rc-manager.conf", OLD_GUIDE_RC_MANAGER)
        resolv_conf = self.write(
            self.work / "etc/resolv.conf",
            "# Generated by resolvconf\nnameserver 127.0.0.1\n",
        )
        tasks = (
            self.detection_slice()
            + self.task_slice(
                "Move NetworkManager profiles off the loopback relay",
                "Remove files of the former DNS setup after backup",
            )
            + self.task_slice(
                "Inspect resolv.conf", "Require systemd-resolved to answer queries"
            )
        )
        tasks[
            [task["name"] for task in tasks].index(
                "Remove files of the former DNS setup after backup"
            )
        ].pop("notify")
        output = self.run_play(
            tasks,
            {
                "system_dns_relay_files": [str(relay)],
                "system_dns_legacy_files": [str(legacy)],
                "system_dns_backup_dir": str(self.work / "backup"),
                "system_dns_resolv_conf": str(resolv_conf),
                "system_dns_resolved_stub": str(self.work / "run/stub-resolv.conf"),
            },
            "--check",
        )
        self.assertNotRegex(output, r"changed=0\b")
        self.assertFalse((self.work / "backup").exists())
        self.assertTrue(relay.exists() and legacy.exists())
        self.assertFalse(resolv_conf.is_symlink())

    def dnsmasq_stop_decision(self, relay_found, docker_selected):
        task = self.task_slice(
            "Stop and disable the standalone dnsmasq relay",
            "Stop and disable the standalone dnsmasq relay",
        )[0]
        # Stand in for systemctl, keeping the condition.
        task.pop("ansible.builtin.systemd_service")
        task.pop("notify")
        task["ansible.builtin.debug"] = {"msg": "DNSMASQ STOPPED"}
        output = self.run_play(
            [task],
            {
                "system_dns_dnsmasq_unit": {"stat": {"exists": True}},
                "system_dns_relay_found": relay_found,
                "system_dns_docker_selected": docker_selected,
            },
        )
        return "DNSMASQ STOPPED" in output

    def test_dnsmasq_is_stopped_only_when_it_served_as_the_relay(self):
        self.assertTrue(self.dnsmasq_stop_decision(True, False))
        self.assertTrue(self.dnsmasq_stop_decision(True, True))
        self.assertFalse(self.dnsmasq_stop_decision(False, True))
        self.assertFalse(self.dnsmasq_stop_decision(False, False))

    def port_check(self, listeners, relay_present, succeed=True):
        if relay_present:
            self.write(self.relay_file, "server=192.0.2.1\n")
        unit = self.write(self.work / "units/dnsmasq.service", "[Unit]\n")
        self.environment["FAKE_SS_OUTPUT"] = listeners
        tasks = self.task_slice(
            "Add the Docker bridge to the resolved stub listeners",
            "Require the Docker bridge address to be free for resolved",
        )
        return self.run_play(
            tasks,
            {
                "system_dns_docker_selected": True,
                "system_unit_directory": str(unit.parent),
                "system_dns_relay_files": [str(self.relay_file)],
                "system_dns_legacy_files": [],
            },
            succeed=succeed,
        )

    def test_foreign_port_53_listeners_stop_the_play_before_any_change(self):
        for listeners in [SS_WILDCARD_DNSMASQ, SS_BRIDGE_UNBOUND]:
            with self.subTest(listeners=listeners):
                output = self.port_check(listeners, relay_present=False, succeed=False)
                self.assertIn("Another program listens on port 53", output)

    def test_resolved_libvirt_and_the_relay_dnsmasq_do_not_conflict(self):
        self.port_check(SS_RESOLVED, relay_present=False)
        self.port_check(SS_WILDCARD_DNSMASQ, relay_present=True)

    def resolv_conf_play(
        self, resolv_conf, stub, *arguments, succeed=True, **variables
    ):
        tasks = self.task_slice(
            "Inspect resolv.conf", "Require systemd-resolved to answer queries"
        )
        return self.run_play(
            tasks,
            {
                "system_dns_resolv_conf": str(resolv_conf),
                "system_dns_resolved_stub": str(stub),
                "system_dns_backup_dir": str(self.work / "backup"),
                **variables,
            },
            *arguments,
            succeed=succeed,
        )

    def stub(self):
        return self.write(
            self.work / "run/stub-resolv.conf", STUB_HEADER + "nameserver 127.0.0.53\n"
        )

    def test_managed_regular_resolv_conf_is_backed_up_then_linked_to_the_stub(self):
        stub = self.stub()
        for name, content in [
            ("openresolv", "# Generated by resolvconf\nnameserver 127.0.0.1\n"),
            ("networkmanager", "# Generated by NetworkManager\nnameserver 192.0.2.1\n"),
            ("stub-copy", STUB_HEADER + "nameserver 127.0.0.53\nsearch home\n"),
            ("uplink-copy", UPLINK_HEADER + "nameserver 192.0.2.1\n"),
            ("relay", "nameserver 127.0.0.1\n"),
            ("headerless-stub-copy", "nameserver 127.0.0.53\nnameserver 127.0.0.54\n"),
        ]:
            with self.subTest(name=name):
                resolv_conf = self.write(self.work / name / "resolv.conf", content)
                self.resolv_conf_play(resolv_conf, stub)
                self.assertEqual(os.readlink(resolv_conf), str(stub))
                backup = Path(f"{self.work / 'backup'}{resolv_conf}")
                self.assertEqual(backup.read_text(), content)
                self.assertRegex(
                    self.resolv_conf_play(resolv_conf, stub), r"changed=0\b"
                )

    def test_resolv_conf_owned_by_a_vpn_client_is_left_alone(self):
        stub = self.stub()
        content = VPN_HEADER + "nameserver 192.0.2.10\nsearch corp.example\n"
        resolv_conf = self.write(self.work / "etc/resolv.conf", content)
        saved = self.write(
            self.work / "etc/resolv.conf.forticlient.backup",
            UPLINK_HEADER + "nameserver 192.0.2.1\n",
        )
        output = self.resolv_conf_play(resolv_conf, stub)
        self.assertFalse(resolv_conf.is_symlink())
        self.assertEqual(resolv_conf.read_text(), content)
        self.assertEqual(saved.read_text(), UPLINK_HEADER + "nameserver 192.0.2.1\n")
        self.assertFalse((self.work / "backup").exists())
        self.assertIn("written by another program", output)
        self.assertIn("generated by forticlient", output)
        self.assertIn("after disconnecting", output)

    def test_override_links_a_foreign_resolv_conf(self):
        stub = self.stub()
        content = VPN_HEADER + "nameserver 192.0.2.10\n"
        resolv_conf = self.write(self.work / "etc/resolv.conf", content)
        output = self.resolv_conf_play(
            resolv_conf, stub, system_dns_force_resolv_conf_link=True
        )
        self.assertEqual(os.readlink(resolv_conf), str(stub))
        self.assertEqual(
            Path(f"{self.work / 'backup'}{resolv_conf}").read_text(), content
        )
        self.assertNotIn("written by another program", output)

    def test_relative_link_to_the_stub_is_kept(self):
        self.stub()
        resolv_conf = self.work / "etc/resolv.conf"
        resolv_conf.parent.mkdir()
        resolv_conf.symlink_to("../run/stub-resolv.conf")
        self.assertRegex(
            self.resolv_conf_play(resolv_conf, self.work / "run/stub-resolv.conf"),
            r"changed=0\b",
        )
        self.assertEqual(os.readlink(resolv_conf), "../run/stub-resolv.conf")

    def test_link_to_another_resolver_is_replaced(self):
        stub = self.stub()
        other = self.write(
            self.work / "run/resolv.conf", UPLINK_HEADER + "nameserver 192.0.2.1\n"
        )
        resolv_conf = self.work / "etc/resolv.conf"
        resolv_conf.parent.mkdir()
        resolv_conf.symlink_to(other)
        self.resolv_conf_play(resolv_conf, stub)
        self.assertEqual(os.readlink(resolv_conf), str(stub))

    def test_resolv_conf_is_not_linked_when_the_stub_is_missing(self):
        resolv_conf = self.write(
            self.work / "etc/resolv.conf", "nameserver 127.0.0.1\n"
        )
        output = self.resolv_conf_play(
            resolv_conf, self.work / "run/stub-resolv.conf", succeed=False
        )
        self.assertIn("was not linked to it", output)
        self.assertFalse(resolv_conf.is_symlink())
        self.assertEqual(resolv_conf.read_text(), "nameserver 127.0.0.1\n")

    def test_play_fails_when_resolved_does_not_answer(self):
        stub = self.stub()
        resolv_conf = self.write(
            self.work / "etc/resolv.conf", "nameserver 127.0.0.1\n"
        )
        self.environment["FAKE_RESOLVECTL_RC"] = "1"
        output = self.resolv_conf_play(resolv_conf, stub, succeed=False)
        self.assertIn("did not answer a query for localhost", output)

    def docker_block(self):
        block = self.task_slice(
            "Point Docker containers at the resolved bridge listener",
            "Point Docker containers at the resolved bridge listener",
        )
        block[0]["block"][-1].pop("notify")
        return block

    def test_docker_configuration_is_merged_once(self):
        daemon = self.work / "docker/daemon.json"
        original = {
            "dns": ["10.184.1.1"],
            "log-opts": {"max-size": "100m"},
            "runtimes": {"nvidia": {"args": [], "path": "nvidia-container-runtime"}},
        }
        self.write(daemon, json.dumps(original))
        block = self.docker_block()
        variables = {
            "system_dns_docker_selected": True,
            "system_docker_daemon_config_path": str(daemon),
        }
        self.run_play(block, variables)
        written = json.loads(daemon.read_text())
        self.assertEqual(written, {**original, "bip": "10.184.1.1/28"})
        self.assertRegex(self.run_play(block, variables), r"changed=0\b")

    def test_empty_docker_configuration_is_read_as_an_empty_object(self):
        daemon = self.work / "docker/daemon.json"
        for content in ["", " \n"]:
            with self.subTest(content=content):
                self.write(daemon, content)
                self.run_play(
                    self.docker_block(),
                    {
                        "system_dns_docker_selected": True,
                        "system_docker_daemon_config_path": str(daemon),
                    },
                )
                self.assertEqual(
                    json.loads(daemon.read_text()),
                    {"bip": "10.184.1.1/28", "dns": ["10.184.1.1"]},
                )

    def test_fixed_cidr_outside_the_bridge_stops_the_play(self):
        original = '{"fixed-cidr": "172.17.5.0/24"}'
        daemon = self.write(self.work / "docker/daemon.json", original)
        output = self.run_play(
            self.docker_block(),
            {
                "system_dns_docker_selected": True,
                "system_docker_daemon_config_path": str(daemon),
            },
            succeed=False,
        )
        self.assertIn("outside the bridge network", output)
        self.assertEqual(daemon.read_text(), original)

    def detection_tasks(self):
        tasks = self.task_slice(
            "Look for the nmcli client", "Apply the DNS policy", source=DETECTION
        )
        # Stand in for the policy import, keeping its condition.
        policy = tasks[-1]
        policy.pop("ansible.builtin.import_tasks")
        policy["ansible.builtin.debug"] = {"msg": "POLICY APPLIED"}
        return tasks

    def run_detection(self, services):
        return self.run_play(
            self.detection_tasks(), {"ansible_facts": {"services": services}}
        )

    def test_policy_runs_when_resolved_networkmanager_and_nmcli_exist(self):
        output = self.run_detection(RUNNING_SERVICES)
        self.assertIn("POLICY APPLIED", output)
        self.assertNotIn("DNS policy skipped", output)

    def test_policy_is_skipped_without_systemd_resolved(self):
        output = self.run_detection({"NetworkManager.service": {"state": "running"}})
        self.assertNotIn("POLICY APPLIED", output)
        self.assertIn("DNS policy skipped", output)
        self.assertIn("systemd-resolved.service", output)

    def test_policy_is_skipped_while_networkmanager_is_stopped(self):
        output = self.run_detection(
            {**RUNNING_SERVICES, "NetworkManager.service": {"state": "stopped"}}
        )
        self.assertNotIn("POLICY APPLIED", output)
        self.assertIn("NetworkManager.service (running)", output)

    def test_policy_is_skipped_without_nmcli(self):
        # Link every host command except nmcli, so a host nmcli is not found
        # while Ansible keeps the shell tools it needs.
        host = self.work / "host-bin"
        host.mkdir()
        for directory in os.environ["PATH"].split(os.pathsep):
            if not os.path.isdir(directory):
                continue
            for name in os.listdir(directory):
                target = host / name
                if name != "nmcli" and not target.is_symlink():
                    target.symlink_to(os.path.join(directory, name))
        self.path = str(host)
        output = self.run_detection(RUNNING_SERVICES)
        self.assertNotIn("POLICY APPLIED", output)
        self.assertIn("Missing: nmcli", output)


if __name__ == "__main__":
    unittest.main()
