"""Audio role: site wiring, the voice effect group and the rendered PipeWire files."""

import configparser
import hashlib
import itertools
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from ansible_test_environment import ansible_test_environment

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "ansible/site.yml"
ROLE = ROOT / "ansible/roles/audio"
DOTFILES = ROOT / "ansible/roles/dotfiles"
ARCH_GROUPS = yaml.safe_load(
    (ROOT / "ansible/roles/packages/vars/archlinux.yml").read_text()
)["packages_family_groups"]["Archlinux"]
WORKSTATION = yaml.safe_load(
    (ROOT / "ansible/group_vars/all/packages.yml").read_text()
)["packages_workstation_groups"]
DEFAULTS = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
# Options that libspa-aec-webrtc (PipeWire 1.6) reads; any other key is
# silently ignored, as webrtc.highpass_filter and webrtc.extended_filter were.
WEBRTC_KEYS = {
    "gain_control",
    "high_pass_filter",
    "mobile_mode",
    "noise_suppression",
    "transient_suppression",
    "voice_detection",
}
EFFECTS = {"vader", "chipmunk", "robot", "church", "radio"}
REALTIME = "pipewire/pipewire.conf.d/10-realtime.conf"
REALTIME_SHIPPED = """# Override the arguments of PipeWire's existing realtime module.
module.rt.args = {
    nice.level = -11
    rt.prio    = 88
}
"""


class AudioWiringTests(unittest.TestCase):
    def test_role_runs_with_the_dotfiles_and_skips_plans(self):
        entry = next(
            role
            for role in yaml.safe_load(SITE.read_text())[0]["roles"]
            if role["role"] == "audio"
        )
        self.assertEqual(entry["tags"], ["dotfiles", "audio"])
        self.assertFalse(entry["become"])
        self.assertIn("!= 'plan'", entry["when"])

    def test_dotfiles_role_no_longer_ships_the_audio_files(self):
        defaults = yaml.safe_load((DOTFILES / "defaults/main.yml").read_text())
        for directory in (".config/pipewire", ".config/wireplumber"):
            self.assertNotIn(directory, defaults["dotfiles_directories"])
            self.assertNotIn(directory, defaults["dotfiles_directory_handlers"])
            self.assertFalse((DOTFILES / "files/home" / directory).exists())
        handlers = yaml.safe_load((DOTFILES / "handlers/main.yml").read_text())
        self.assertNotIn(
            "Apply changed user audio configuration",
            [handler["name"] for handler in handlers],
        )

    def test_voice_effect_group_holds_the_ladspa_plugins_and_is_default(self):
        self.assertEqual(ARCH_GROUPS["26_voice_effects"], ["swh-plugins"])
        self.assertNotIn("swh-plugins", ARCH_GROUPS["01_base"])
        self.assertIn("noise-suppression-for-voice", ARCH_GROUPS["01_base"])
        self.assertIn("26_voice_effects", WORKSTATION)
        self.assertEqual(DEFAULTS["audio_voice_effects_group"], "26_voice_effects")

    def test_echo_cancel_options_are_read_by_the_webrtc_module(self):
        self.assertLessEqual(set(DEFAULTS["audio_echo_cancel_args"]), WEBRTC_KEYS)

    def test_kept_effects_and_unique_node_names(self):
        effects = DEFAULTS["audio_voice_effects"]
        self.assertEqual({effect["name"] for effect in effects}, EFFECTS)
        for effect in effects:
            names = [node["name"] for node in effect["nodes"]]
            self.assertEqual(len(names), len(set(names)), effect["name"])

    def test_obsolete_checksum_matches_the_shipped_realtime_file(self):
        shipped = hashlib.sha1(REALTIME_SHIPPED.encode(), usedforsecurity=False)
        self.assertEqual(
            DEFAULTS["audio_obsolete_files"], {REALTIME: shipped.hexdigest()}
        )


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
class PulseClientRestartTests(unittest.TestCase):
    """The audio handler restarts pipewire-pulse; SwayOSD must follow it."""

    UNITS = DOTFILES / "files/home/.config/systemd/user"

    def test_swayosd_server_restarts_with_pipewire_pulse(self):
        unit = configparser.ConfigParser(strict=False, interpolation=None)
        unit.read(self.UNITS / "swayosd-server.service")
        self.assertIn("pipewire-pulse.service", unit["Unit"]["PartOf"].split())
        self.assertIn("pipewire-pulse.service", unit["Unit"]["After"].split())
        self.assertEqual(unit["Service"]["ExecStart"], "/usr/bin/swayosd-server")
        link = self.UNITS / "graphical-session.target.wants/swayosd-server.service"
        self.assertEqual(os.readlink(link), "../swayosd-server.service")

    def test_hyprland_no_longer_launches_its_own_swayosd_server(self):
        config = (DOTFILES / "files/home/.config/hypr/config.lua").read_text()
        self.assertNotIn('"/usr/bin/swayosd-server"', config)


class AudioRoleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.config = self.work / "home/.config"
        self.pipewire = self.config / "pipewire/pipewire.conf.d"
        self.wireplumber = self.config / "wireplumber/wireplumber.conf.d"
        binary = self.work / "bin"
        binary.mkdir()
        self.log = self.work / "systemctl.log"
        systemctl = binary / "systemctl"
        systemctl.write_text(f'#!/bin/sh\necho "$*" >> "{self.log}"\n')
        systemctl.chmod(0o755)
        self.environment = ansible_test_environment(self.work)
        self.environment["ANSIBLE_ROLES_PATH"] = str(ROOT / "ansible/roles")
        self.path = f"{binary}:{os.environ['PATH']}"

    def run_role(
        self, os_family="Archlinux", groups=("26_voice_effects",), succeed=True, **extra
    ):
        playbook = self.work / "play.yml"
        playbook.write_text(
            yaml.safe_dump(
                [
                    {
                        "hosts": "localhost",
                        "connection": "local",
                        "gather_facts": False,
                        "environment": {"PATH": self.path},
                        "vars": {
                            "packages_selected_groups": list(groups),
                            "audio_config_home": str(self.config),
                            **extra,
                        },
                        "pre_tasks": [
                            {
                                "name": "Provide isolated facts",
                                "ansible.builtin.set_fact": {
                                    "ansible_facts": {"os_family": os_family}
                                },
                            }
                        ],
                        "roles": ["audio"],
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
        output = result.stdout + result.stderr
        if succeed:
            self.assertEqual(result.returncode, 0, output)
        else:
            self.assertNotEqual(result.returncode, 0, output)
        return result.stdout

    def assert_smart_filter_chain(self, text, chain):
        """chain lists the filters from the applications to the microphone."""
        # The wiring must come from the smart filter chain alone: a stage that
        # targets another one, or a priority that makes a stage the default
        # source, lets the chain record itself.
        for wiring in ("target.object", "priority.session", "node.dont-fallback"):
            self.assertNotIn(wiring, text)
        names = re.findall(r'filter\.smart\.name\s*= "([^"]+)"', text)
        self.assertEqual(sorted(names), sorted(chain))
        self.assertEqual(len(re.findall(r"filter\.smart\s*= true", text)), len(chain))
        self.assertEqual(
            len(re.findall(r"filter\.smart\.targetable\s*= true", text)), len(chain)
        )
        for nearer, farther in itertools.pairwise(chain):
            self.assertRegex(
                text, rf'filter\.smart\.before\s*= \[ "{re.escape(farther)}" \]'
            )
            self.assertRegex(
                text, rf'filter\.smart\.after\s*= \[ "{re.escape(nearer)}" \]'
            )
        if len(chain) == 1:
            self.assertNotRegex(text, r"filter\.smart\.(before|after)\s*=")

    @unittest.skipUnless(shutil.which("spa-json-dump"), "requires spa-json-dump")
    def test_rendered_files_are_valid_spa_json(self):
        quoted = {
            "name": "quoted",
            "description": 'Voix "test" \\ fin',
            "nodes": [
                {
                    "type": "builtin",
                    "name": "gain",
                    "label": "bq_highshelf",
                    "control": {"Freq": 1000.0, "Q": 0.707, "Gain": 1.0},
                }
            ],
        }
        for os_family in ("Archlinux", "Debian"):
            with self.subTest(os_family=os_family):
                self.run_role(
                    os_family=os_family,
                    audio_voice_effects=[*DEFAULTS["audio_voice_effects"], quoted],
                )
                for path in [*self.pipewire.iterdir(), *self.wireplumber.iterdir()]:
                    result = subprocess.run(
                        ["spa-json-dump", str(path)],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0, f"{path}: {result.stderr}")

    def test_arch_host_gets_rnnoise_and_every_effect(self):
        output = self.run_role()
        echo = (self.pipewire / "20-echo-cancel.conf").read_text()
        effects = (self.pipewire / "30-voice-effects.conf").read_text()

        self.assertEqual(
            set(re.findall(r"webrtc\.(\w+)", echo)), WEBRTC_KEYS - {"mobile_mode"}
        )
        self.assertIn("webrtc.noise_suppression = false", echo)
        self.assertIn("label = noise_suppressor_mono", echo)
        self.assert_smart_filter_chain(echo, ["voice.clean", "voice.echo-cancel"])
        self.assertIn('node.name = "voice.echo-cancel.monitor"', echo)
        self.assertEqual(echo.count("flags = [ nofail ]"), 2)
        self.assertEqual(
            set(re.findall(r'node\.name\s*= "([^"]+)"', echo)),
            {
                "voice.clean",
                "voice.clean.capture",
                "voice.echo-cancel",
                "voice.echo-cancel.capture",
                "voice.echo-cancel.monitor",
            },
        )

        sources = set(re.findall(r'node\.name = "voice\.(\w+)"  media', effects))
        self.assertEqual(sources, EFFECTS)
        for effect in EFFECTS:
            self.assertIn(f'node.name = "voice.{effect}.capture"', effects)
        self.assertNotIn("Microphone (", effects)
        self.assertEqual(effects.count('target.object = "voice.clean"'), len(EFFECTS))
        self.assertEqual(effects.count("flags = [ nofail ]"), len(EFFECTS))
        self.assertNotIn("/usr/lib/ladspa", effects)
        self.assertIn('{ output = "presence:Out"  input = "limit:Input 1" }', effects)
        self.assertIn('outputs = [ "limit:Output 1" ]', effects)
        self.assertIn('outputs = [ "reverb:Left output" ]', effects)

        bluez = (self.wireplumber / "50-bluez-config.conf").read_text()
        self.assertNotRegex(bluez, r"(?m)^\s*bluez5\.codecs")
        self.assertNotIn("ldac.quality", bluez)
        self.assertTrue((self.wireplumber / "50-disable-suspend.conf").is_file())

        self.assertIn("RUNNING HANDLER [audio : Apply changed user audio", output)
        self.assertEqual(
            self.log.read_text(),
            "--user --no-block try-reload-or-restart pipewire.service "
            "pipewire-pulse.service wireplumber.service\n",
        )
        self.log.unlink()
        self.assertIn("changed=0", self.run_role())
        self.assertFalse(self.log.exists())

    def test_without_rnnoise_the_echo_canceller_is_the_clean_source(self):
        self.run_role(os_family="Debian")
        echo = (self.pipewire / "20-echo-cancel.conf").read_text()
        self.assertNotIn("filter-chain", echo)
        self.assert_smart_filter_chain(echo, ["voice.clean"])
        self.assertEqual(
            set(re.findall(r'node\.name\s*= "([^"]+)"', echo)),
            {"voice.clean", "voice.clean.capture", "voice.clean.monitor"},
        )
        self.assertIn("webrtc.noise_suppression = true", echo)

    def test_host_settings_remove_the_effects_and_the_suspend_policy(self):
        self.run_role()
        self.run_role(groups=(), audio_disable_suspend=False)
        self.assertFalse((self.pipewire / "30-voice-effects.conf").exists())
        self.assertFalse((self.wireplumber / "50-disable-suspend.conf").exists())
        self.assertTrue((self.pipewire / "20-echo-cancel.conf").is_file())

    def test_shipped_realtime_file_is_deleted_and_an_edited_one_kept(self):
        realtime = self.config / REALTIME
        realtime.parent.mkdir(parents=True)
        realtime.write_text(REALTIME_SHIPPED)
        self.run_role()
        self.assertFalse(realtime.exists())

        realtime.write_text(REALTIME_SHIPPED.replace("88", "90"))
        output = self.run_role()
        self.assertTrue(realtime.exists())
        self.assertIn("was changed by hand, so it is kept.", output)

    def test_linked_realtime_file_is_kept_and_reported(self):
        realtime = self.config / REALTIME
        realtime.parent.mkdir(parents=True)
        shipped = self.work / "shipped.conf"
        shipped.write_text(REALTIME_SHIPPED)
        realtime.symlink_to(shipped)
        output = self.run_role()
        self.assertTrue(realtime.is_symlink())
        self.assertIn("is not a regular file, so it is kept.", output)

    def test_linked_configuration_directory_is_refused(self):
        clone = self.work / "clone/pipewire"
        clone.mkdir(parents=True)
        self.config.mkdir(parents=True)
        (self.config / "pipewire").symlink_to(clone)
        output = self.run_role(succeed=False)
        self.assertIn(
            "Refuse to write through a linked configuration directory", output
        )
        self.assertEqual(list(clone.iterdir()), [])
        self.assertFalse(self.log.exists())

    def test_strings_are_escaped_for_spa_json(self):
        effect = {
            "name": "quoted",
            "description": 'Voix "test"',
            "nodes": [{"type": "builtin", "name": "gain", "label": "bq_highshelf"}],
        }
        self.run_role(audio_voice_effects=[effect])
        effects = (self.pipewire / "30-voice-effects.conf").read_text()
        self.assertIn('node.description = "Voix \\"test\\""', effects)
        self.assertIn('node.name = "voice.quoted.capture"', effects)


if __name__ == "__main__":
    unittest.main()
