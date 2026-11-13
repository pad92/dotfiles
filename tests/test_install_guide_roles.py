"""Tests for the roles that automate the post-install steps of the Arch guide."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from ansible_test_environment import ansible_test_environment

ROOT = Path(__file__).resolve().parents[1]
ROLES = ROOT / "ansible/roles"
COLLECTIONS = ROOT / ".ansible/collections"

ARCH_LOGIN = """#%PAM-1.0

auth       requisite    pam_nologin.so
auth       include      system-local-login
account    include      system-local-login
session    include      system-local-login
password   include      system-local-login
"""


def load_tasks(role, without=()):
    """Load a role's tasks, dropping the ones that need root or systemd."""
    tasks = yaml.safe_load((ROLES / role / "tasks/main.yml").read_text())
    return [task for task in tasks if task["name"] not in without]


def load_defaults(role):
    return yaml.safe_load((ROLES / role / "defaults/main.yml").read_text())


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
class InstallGuideRoleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)

    def run_play(self, play, expect_success=True):
        playbook = self.work / "play.yml"
        playbook.write_text(
            yaml.safe_dump(
                [
                    {"hosts": "localhost", "connection": "local", "gather_facts": False}
                    | play
                ]
            )
        )
        result = subprocess.run(
            ["ansible-playbook", "-i", "localhost,", str(playbook)],
            cwd=ROOT,
            env={
                **ansible_test_environment(self.work),
                "ANSIBLE_COLLECTIONS_PATH": str(COLLECTIONS),
            },
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        output = result.stdout + result.stderr
        if expect_success:
            self.assertEqual(result.returncode, 0, output)
        return output

    # package_services: groups created by a selected package group.
    def run_user_groups(self, groups, existing):
        tasks = load_tasks("package_services")
        start = next(
            index
            for index, task in enumerate(tasks)
            if task["name"] == "Validate the users who join package groups"
        )
        tasks = [
            task
            for task in tasks[start:]
            if task["name"]
            not in [
                "Read the system groups",
                "Add the regular users to the selected groups",
            ]
        ]
        defaults = load_defaults("package_services")
        return self.run_play(
            {
                "vars": {
                    "ansible_facts": {
                        "os_family": "Archlinux",
                        "getent_group": {name: ["x", "1"] for name in existing},
                    },
                    "package_services_user_groups_by_group": defaults[
                        "package_services_user_groups_by_group"
                    ],
                    "package_services_group_users": ["alice"],
                    "packages_selected_groups": groups,
                },
                "tasks": tasks
                + [
                    {
                        "ansible.builtin.debug": {
                            "msg": "JOIN {{ package_services_user_groups_present }}"
                        }
                    }
                ],
            }
        )

    def test_base_group_users_join_realtime(self):
        output = self.run_user_groups(["01_base"], ["realtime", "wheel"])
        self.assertIn("JOIN ['realtime']", output)

    def test_missing_realtime_group_is_reported_not_created(self):
        output = self.run_user_groups(["01_base"], ["wheel"])
        self.assertIn("JOIN []", output)
        self.assertIn("group does not exist: realtime", output)

    def test_unselected_base_group_joins_nothing(self):
        output = self.run_user_groups(["20_apps"], ["realtime"])
        self.assertIn("JOIN []", output)

    def test_base_group_enables_the_weekly_trim(self):
        defaults = load_defaults("package_services")
        self.assertIn(
            "fstrim.timer",
            defaults["package_services_by_group"]["Archlinux"]["01_base"],
        )

    # time_sync: never run two NTP clients.
    def run_time_sync(self, services):
        tasks = load_tasks(
            "time_sync",
            without=["Read the service states", "Enable and start systemd-timesyncd"],
        )
        return self.run_play(
            {
                "vars": {
                    **load_defaults("time_sync"),
                    "ansible_facts": {"services": services},
                },
                "tasks": tasks
                + [
                    {
                        "ansible.builtin.debug": {
                            "msg": "ENABLE {{ time_sync_others | length == 0 and "
                            "time_sync_unit in ansible_facts.services }}"
                        }
                    }
                ],
            }
        )

    def test_timesyncd_is_enabled_without_another_client(self):
        output = self.run_time_sync(
            {
                "systemd-timesyncd.service": {"state": "stopped", "status": "disabled"},
                "chronyd.service": {"state": "stopped", "status": "disabled"},
            }
        )
        self.assertIn("ENABLE True", output)

    def test_running_chrony_keeps_timesyncd_untouched(self):
        output = self.run_time_sync(
            {
                "systemd-timesyncd.service": {"state": "stopped", "status": "disabled"},
                "chronyd.service": {"state": "running", "status": "disabled"},
            }
        )
        self.assertIn("ENABLE False", output)
        self.assertIn("chronyd.service already synchronizes the clock", output)

    def test_enabled_ntpd_keeps_timesyncd_untouched(self):
        output = self.run_time_sync(
            {
                "systemd-timesyncd.service": {"state": "stopped", "status": "disabled"},
                "ntpd.service": {"state": "stopped", "status": "enabled"},
            }
        )
        self.assertIn("ENABLE False", output)

    # power_save: options for the loaded modules, on a portable machine only.
    def run_power_save(self, form_factor, modules, **extra_vars):
        module_directory = self.work / "module"
        for module in modules:
            (module_directory / module).mkdir(parents=True, exist_ok=True)
        tasks = load_tasks("power_save")
        for task in tasks:
            for module in ("ansible.builtin.template", "ansible.builtin.file"):
                if module in task:
                    task[module].pop("owner", None)
                    task[module].pop("group", None)
                    if module == "ansible.builtin.template":
                        task[module]["src"] = str(
                            ROLES / "power_save/templates" / task[module]["src"]
                        )
        target = self.work / "power-save.conf"
        output = self.run_play(
            {
                "vars": {
                    **load_defaults("power_save"),
                    "ansible_facts": {"form_factor": form_factor},
                    "power_save_module_directory": str(module_directory),
                    "power_save_modprobe_path": str(target),
                    **extra_vars,
                },
                "tasks": tasks,
                "handlers": yaml.safe_load(
                    (ROLES / "power_save/handlers/main.yml").read_text()
                ),
            }
        )
        return output, target

    def test_laptop_gets_wifi_and_audio_power_saving(self):
        _, target = self.run_power_save(
            "Notebook", ["iwlwifi", "iwlmvm", "snd_hda_intel", "cfg80211"]
        )
        options = [
            line
            for line in target.read_text().splitlines()
            if line.startswith("options")
        ]
        self.assertEqual(
            options,
            [
                "options iwlwifi power_save=1 uapsd_disable=0",
                "options iwlmvm power_scheme=3",
                "options snd_hda_intel power_save=1",
            ],
        )

    def test_dvm_firmware_gets_its_own_option(self):
        _, target = self.run_power_save("Laptop", ["iwlwifi", "iwldvm"])
        self.assertIn("options iwldvm force_cam=0", target.read_text())
        self.assertNotIn("iwlmvm", target.read_text())

    def test_desktop_gets_no_power_saving_and_old_file_is_removed(self):
        (self.work / "power-save.conf").write_text("options iwlwifi power_save=1\n")
        _, target = self.run_power_save("Desktop", ["iwlwifi", "snd_hda_intel"])
        self.assertFalse(target.exists())

    def test_power_saving_can_be_forced_on_a_desktop(self):
        _, target = self.run_power_save(
            "Desktop", ["snd_hda_intel"], power_save_mode=True
        )
        self.assertIn("options snd_hda_intel power_save=1", target.read_text())

    def test_power_saving_rerun_changes_nothing(self):
        self.run_power_save("Notebook", ["iwlwifi", "snd_hda_intel"])
        output, _ = self.run_power_save("Notebook", ["iwlwifi", "snd_hda_intel"])
        self.assertIn("changed=0", output)

    # wireless_regdom: one active country in the wireless-regdb file.
    def run_regdom(self, config, regdom="FR"):
        return self.run_play(
            {
                "vars": {
                    "wireless_regdom_country": regdom,
                    "wireless_regdom_config": str(config),
                },
                "roles": [{"role": str(ROLES / "wireless_regdom")}],
            }
        )

    def test_regdom_replaces_another_active_country(self):
        config = self.work / "wireless-regdom"
        config.write_text(
            '#WIRELESS_REGDOM="DE"\nWIRELESS_REGDOM="US"\n#WIRELESS_REGDOM="FR"\n'
        )
        self.run_regdom(config)
        active = [
            line for line in config.read_text().splitlines() if not line.startswith("#")
        ]
        self.assertEqual(active, ['WIRELESS_REGDOM="FR"'])
        self.assertIn("changed=0", self.run_regdom(config))

    def test_regdom_rejects_a_lowercase_code(self):
        config = self.work / "wireless-regdom"
        config.write_text('#WIRELESS_REGDOM="FR"\n')
        playbook_output = self.run_play(
            {
                "vars": {
                    "wireless_regdom_country": "fr",
                    "wireless_regdom_config": str(config),
                },
                "roles": [{"role": str(ROLES / "wireless_regdom")}],
            },
            expect_success=False,
        )
        self.assertIn("two-letter uppercase country code", playbook_output)

    # gnome_keyring: PAM rules after the system-local-login includes.
    def run_gnome_keyring(self, login):
        pam_directory = self.work / "pam.d"
        pam_directory.mkdir(exist_ok=True)
        (pam_directory / "login").write_text(login)
        module = self.work / "pam_gnome_keyring.so"
        module.touch()
        output = self.run_play(
            {
                "vars": {
                    "gnome_keyring_pam_directory": str(pam_directory),
                    "gnome_keyring_pam_module": str(module),
                },
                "roles": [{"role": str(ROLES / "gnome_keyring")}],
            }
        )
        return output, (pam_directory / "login").read_text()

    @unittest.skipUnless(COLLECTIONS.is_dir(), "requires pinned Ansible collections")
    def test_login_unlocks_the_keyring_once(self):
        _, login = self.run_gnome_keyring(ARCH_LOGIN)
        rules = [line.split() for line in login.splitlines() if "gnome" in line]
        self.assertEqual(
            rules,
            [
                ["-auth", "optional", "pam_gnome_keyring.so"],
                ["-session", "optional", "pam_gnome_keyring.so", "auto_start"],
                ["-password", "optional", "pam_gnome_keyring.so", "use_authtok"],
            ],
        )
        lines = [
            line.split()[:2] for line in login.splitlines() if line and line[0] != "#"
        ]
        self.assertLess(
            lines.index(["auth", "include"]), lines.index(["-auth", "optional"])
        )
        output, again = self.run_gnome_keyring(login)
        self.assertIn("changed=0", output)
        self.assertEqual(login, again)

    @unittest.skipUnless(COLLECTIONS.is_dir(), "requires pinned Ansible collections")
    def test_login_without_system_local_login_is_reported(self):
        output, login = self.run_gnome_keyring(
            "#%PAM-1.0\nauth required pam_unix.so\nsession required pam_unix.so\n"
        )
        self.assertNotIn("gnome", login)
        self.assertIn("Add the pam_gnome_keyring.so rules by hand", output)


if __name__ == "__main__":
    unittest.main()
