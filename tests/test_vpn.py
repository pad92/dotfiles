"""Exercise the Vault-driven SAML VPN: Ansible tasks, polkit rule and Waybar module."""

import json
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
from ansible_test_environment import ansible_test_environment

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "ansible/roles/system/tasks/vpn.yml"
ROLE_MAIN = ROOT / "ansible/roles/system/tasks/main.yml"
DEFAULTS = yaml.safe_load((ROOT / "ansible/roles/system/defaults/main.yml").read_text())
MODULE = ROOT / "ansible/roles/dotfiles/files/home/.config/waybar/modules/vpn"
WAYBAR = ROOT / "ansible/roles/dotfiles/files/home/.config/waybar"
HANDLER = "Reload the systemd manager"
# Documentation range (RFC 6761 .test): never a real gateway.
GATEWAY = "vpn.example.test"


def without_ownership(tasks):
    """Fixtures run unprivileged, so drop the root ownership of managed files."""
    pending = list(tasks)
    while pending:
        node = pending.pop()
        if isinstance(node, dict):
            node.pop("owner", None)
            node.pop("group", None)
            pending.extend(node.values())
        elif isinstance(node, list):
            pending.extend(node)
    return tasks


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
class VpnTaskTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        # The play runs from the work directory, so templates resolve there.
        (self.work / "templates").symlink_to(ROOT / "ansible/roles/system/templates")
        self.units = self.work / "units"
        self.units.mkdir()
        (self.units / "openfortivpn@.service").write_text("[Service]\n")
        # polkit ships rules.d with its own ownership; the role only adds a file.
        (self.work / "rules.d").mkdir()
        self.config_dir = self.work / "openfortivpn"
        self.paths = {
            "system_unit_directory": str(self.units),
            "system_vpn_config_dir": str(self.config_dir),
            "system_vpn_unit_dropin_dir": str(
                self.work / "units.d/openfortivpn@work.service.d"
            ),
            "system_vpn_polkit_rule": str(self.work / "rules.d/60-dotfiles-vpn.rules"),
            "system_vpn_waybar_config": str(self.config_dir / "waybar.json"),
            "system_vpn_users": ["alice"],
        }

    def run_play(self, variables, succeed=True):
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
                            **self.paths,
                            **variables,
                        },
                        "tasks": without_ownership(yaml.safe_load(TASKS.read_text())),
                        "handlers": [
                            {
                                "name": HANDLER,
                                "ansible.builtin.debug": {"msg": f"HANDLER {HANDLER}"},
                            }
                        ],
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
            timeout=120,
            check=False,
        )
        output = result.stdout + result.stderr
        if succeed:
            self.assertEqual(result.returncode, 0, output)
        else:
            self.assertNotEqual(result.returncode, 0, output)
        return output

    def configured(self, **overrides):
        return {
            "vault_vpn_gateway_host": GATEWAY,
            "vault_vpn_gateway_port": 10443,
            **overrides,
        }

    def test_without_vault_nothing_is_created(self):
        output = self.run_play({})
        self.assertIn("VPN skipped", output)
        self.assertFalse(self.config_dir.exists())
        self.assertFalse(Path(self.paths["system_vpn_polkit_rule"]).exists())

    def test_vault_gateway_renders_a_saml_config_that_keeps_resolv_conf(self):
        output = self.run_play(self.configured())
        config = self.config_dir / "work.conf"
        settings = dict(
            line.split(" = ", 1)
            for line in config.read_text().splitlines()
            if line and not line.startswith("#")
        )
        self.assertEqual(
            settings,
            {
                "host": GATEWAY,
                "port": "10443",
                "saml-login": "8020",
                "set-dns": "1",
                "use-resolvconf": "1",
                "pppd-use-peerdns": "0",
            },
        )
        self.assertEqual(config.stat().st_mode & 0o777, 0o600)
        dropin = (
            Path(self.paths["system_vpn_unit_dropin_dir"]) / "60-dotfiles-saml.conf"
        )
        self.assertIn("TimeoutStartSec=5min\n", dropin.read_text())
        self.assertIn("Restart=no\n", dropin.read_text())
        self.assertIn(f"HANDLER {HANDLER}", output)
        self.assertEqual(
            json.loads(Path(self.paths["system_vpn_waybar_config"]).read_text()),
            {
                "unit": "openfortivpn@work.service",
                "login_url": f"https://{GATEWAY}:10443/remote/saml/start?redirect=1",
            },
        )

    def test_second_run_changes_nothing(self):
        self.run_play(self.configured())
        output = self.run_play(self.configured())
        self.assertIn("changed=0", output)
        self.assertNotIn(f"HANDLER {HANDLER}", output)

    def test_values_that_could_inject_settings_are_refused(self):
        for overrides in [
            {"vault_vpn_gateway_host": f"{GATEWAY}\ninsecure-ssl = 1"},
            {"vault_vpn_gateway_host": f"{GATEWAY} trusted-cert"},
            {"vault_vpn_gateway_port": "443\ninsecure-ssl = 1"},
            {"vault_vpn_gateway_port": 0},
            {"vault_vpn_gateway_port": 65536},
            {"system_vpn_saml_port": 80},
            {"system_vpn_name": "../work"},
            {"system_vpn_users": ['alice"; return polkit.Result.YES; //']},
            {"system_vpn_users": "alice"},
        ]:
            # Each case starts clean, so one accepted value cannot fail the others.
            shutil.rmtree(self.config_dir, ignore_errors=True)
            with self.subTest(overrides=overrides):
                output = self.run_play(self.configured(**overrides), succeed=False)
                self.assertIn("Invalid VPN settings", output)
                self.assertFalse(self.config_dir.exists())

    def test_missing_openfortivpn_stops_before_writing(self):
        (self.units / "openfortivpn@.service").unlink()
        output = self.run_play(self.configured(), succeed=False)
        self.assertIn(
            "Install\nopenfortivpn".replace("\n", " "), " ".join(output.split())
        )
        self.assertFalse(self.config_dir.exists())

    @unittest.skipUnless(shutil.which("node"), "requires node")
    def test_polkit_rule_grants_only_start_and_stop_of_the_vpn_unit(self):
        self.run_play(self.configured())
        rule = Path(self.paths["system_vpn_polkit_rule"]).read_text()
        harness = """
const rules = [];
const polkit = {addRule: (f) => rules.push(f), Result: {YES: "yes", NOT_HANDLED: "not_handled"}};
// With node -e, the first extra argument is process.argv[1].
eval(process.argv[1]);
const base = {id: "org.freedesktop.systemd1.manage-units", unit: "openfortivpn@work.service", verb: "start"};
const subject = {user: "alice", local: true, active: true};
const cases = JSON.parse(process.argv[2]);
console.log(JSON.stringify(cases.map(([a, s]) => {
  const action = Object.assign({}, base, a);
  return rules[0]({id: action.id, lookup: (k) => action[k]}, Object.assign({}, subject, s));
})));
"""
        cases = [
            ({}, {}),
            ({"verb": "stop"}, {}),
            ({"verb": "restart"}, {}),
            ({"verb": "enable"}, {}),
            ({"unit": "sshd.service"}, {}),
            ({"id": "org.freedesktop.systemd1.manage-unit-files"}, {}),
            ({}, {"user": "bob"}),
            ({}, {"active": False}),
            ({}, {"local": False}),
        ]
        result = subprocess.run(
            ["node", "-e", harness, rule, json.dumps(cases)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            ["yes", "yes"] + ["not_handled"] * 7,
        )

    def test_role_runs_the_vpn_tasks_under_their_own_tag(self):
        entry = next(
            task
            for task in yaml.safe_load(ROLE_MAIN.read_text())
            if task.get("ansible.builtin.import_tasks") == "vpn.yml"
        )
        self.assertEqual(entry["tags"], ["vpn"])
        self.assertIn("'23_vpn' in", entry["when"][1])

    def test_only_padsp5560_selects_the_vpn_group(self):
        host_groups = yaml.safe_load(
            (ROOT / "ansible/host_vars/localhost.yml").read_text()
        )["packages_host_groups"]
        self.assertEqual(
            sorted(host for host, groups in host_groups.items() if "23_vpn" in groups),
            ["PadsP5560"],
        )
        arch = yaml.safe_load(
            (ROOT / "ansible/roles/packages/vars/archlinux.yml").read_text()
        )
        families = arch["packages_family_groups"]["Archlinux"]
        self.assertEqual(families["23_vpn"], ["openfortivpn"])
        self.assertNotIn("openfortivpn", families["10_sre_devops"])


class VpnWaybarTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.config = Path(temporary.name) / "waybar.json"
        self.api = runpy.run_path(str(MODULE))
        self.api["CONFIG"] = self.config
        # Functions resolve CONFIG through the module globals they share.
        self.api["load_config"].__globals__["CONFIG"] = self.config
        self.state = "inactive"
        self.calls = []

    def write_config(self, **overrides):
        self.config.write_text(
            json.dumps(
                {
                    "unit": "openfortivpn@work.service",
                    "login_url": f"https://{GATEWAY}/remote/saml/start?redirect=1",
                    **overrides,
                }
            )
        )

    def fake_run(self, arguments, **_kwargs):
        self.calls.append(arguments)
        output = self.state if arguments[:2] == ["systemctl", "show"] else ""
        return subprocess.CompletedProcess(arguments, 0, output + "\n", "")

    def test_unmanaged_host_hides_the_module(self):
        with patch("subprocess.run") as run:
            self.assertEqual(self.api["status"](), {"text": ""})
        run.assert_not_called()

    def test_states_map_to_classes(self):
        self.write_config()
        for state, css_class in [
            ("active", "connected"),
            ("activating", "connecting"),
            ("failed", "failed"),
            ("inactive", "disconnected"),
        ]:
            self.state = state
            with (
                self.subTest(state=state),
                patch("subprocess.run", side_effect=self.fake_run),
            ):
                result = self.api["status"]()
                self.assertEqual((result["text"], result["class"]), ("VPN", css_class))

    def test_invalid_config_is_shown_instead_of_hidden(self):
        self.write_config(login_url="http://downgraded.example.test/")
        with patch("subprocess.run", side_effect=self.fake_run):
            result = self.api["status"]()
        self.assertEqual(result["class"], "unknown")
        self.assertIn("login_url", result["tooltip"])

    def test_click_when_disconnected_starts_the_unit_and_opens_the_login(self):
        self.write_config()
        with (
            patch("subprocess.run", side_effect=self.fake_run),
            patch("subprocess.Popen") as popen,
        ):
            self.api["toggle"]()
        self.assertIn(
            ["systemctl", "start", "--no-block", "openfortivpn@work.service"],
            self.calls,
        )
        self.assertEqual(
            popen.call_args.args[0],
            ["xdg-open", f"https://{GATEWAY}/remote/saml/start?redirect=1"],
        )

    def test_click_while_connecting_or_connected_stops_without_opening(self):
        self.write_config()
        for state in ("active", "activating"):
            self.state, self.calls = state, []
            with (
                self.subTest(state=state),
                patch("subprocess.run", side_effect=self.fake_run),
                patch("subprocess.Popen") as popen,
            ):
                self.api["toggle"]()
                popen.assert_not_called()
                self.assertIn(
                    ["systemctl", "stop", "--no-block", "openfortivpn@work.service"],
                    self.calls,
                )

    def test_click_while_disconnecting_neither_restarts_nor_opens_the_login(self):
        # A start issued now would supersede the pending stop job and
        # reconnect behind the user's back.
        self.write_config()
        self.state = "deactivating"
        with (
            patch("subprocess.run", side_effect=self.fake_run),
            patch("subprocess.Popen") as popen,
        ):
            self.api["toggle"]()
        popen.assert_not_called()
        self.assertFalse(
            [call for call in self.calls if call[1:2] in (["start"], ["stop"])],
            self.calls,
        )
        self.assertIn(["pkill", "-RTMIN+9", "-x", "waybar"], self.calls)

    def test_waybar_refresh_signal_matches_the_module_settings(self):
        settings = json.loads((WAYBAR / "conf/system.json").read_text())["custom/vpn"]
        self.assertEqual(settings["signal"], self.api["WAYBAR_SIGNAL"])
        for host in ("config.PadsP5560", "config.PadsTower"):
            self.assertIn(
                "custom/vpn", json.loads((WAYBAR / host).read_text())["modules-right"]
            )


if __name__ == "__main__":
    unittest.main()
