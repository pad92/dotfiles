"""Regression tests for defects found while reviewing the Ansible project."""

import os
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
MARKER = "dotfiles-play-continued"


def fedora_facts(hostname="fixture"):
    return {
        "os_family": "RedHat",
        "distribution": "Fedora",
        "distribution_version": "43",
        "distribution_major_version": "43",
        "hostname": hostname,
    }


@unittest.skipUnless(shutil.which("ansible-playbook"), "requires ansible-playbook")
class AnsibleReviewRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)

    def run_play(self, plays, *arguments, expect_success=True, env=None):
        playbook = self.work / "play.yml"
        playbook.write_text(yaml.safe_dump(plays))
        result = subprocess.run(
            ["ansible-playbook", "-i", "localhost,", str(playbook), *arguments],
            cwd=ROOT,
            env={
                **ansible_test_environment(self.work),
                "ANSIBLE_COLLECTIONS_PATH": str(COLLECTIONS),
                **(env or {}),
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

    def package_role_play(self, **extra_vars):
        return [
            {
                "hosts": "localhost",
                "connection": "local",
                "gather_facts": False,
                "vars": {
                    "ansible_facts": fedora_facts(),
                    "packages_group_selection": [],
                    "packages_state_directory": str(self.work / "state"),
                    **extra_vars,
                },
                "roles": [{"role": str(ROLES / "packages")}],
                "tasks": [{"ansible.builtin.debug": {"msg": MARKER}}],
            }
        ]

    # Check mode must simulate every role, not stop after the package plan.
    @unittest.skipUnless(COLLECTIONS.is_dir(), "requires pinned Ansible collections")
    def test_check_mode_continues_after_package_plan(self):
        output = self.run_play(self.package_role_play(), "--check")
        self.assertIn("Show package plan", output)
        self.assertIn(MARKER, output)

    @unittest.skipUnless(COLLECTIONS.is_dir(), "requires pinned Ansible collections")
    def test_plan_action_still_stops_after_package_plan(self):
        output = self.run_play(self.package_role_play(packages_action="plan"))
        self.assertIn("Show package plan", output)
        self.assertNotIn(MARKER, output)

    @unittest.skipUnless(COLLECTIONS.is_dir(), "requires pinned Ansible collections")
    def test_reconcile_never_removes_configured_protected_packages(self):
        output = self.run_play(
            [
                {
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "ansible_facts": {"os_family": "Debian"},
                        "packages_action": "reconcile",
                        "packages_state_valid": True,
                        "packages_missing_after": [],
                        "packages_selected_groups": ["01_base"],
                        "packages_desired": ["jq"],
                        "packages_installed_after": ["jq", "kept-tool", "old-tool"],
                        "packages_owned_after": ["kept-tool", "old-tool"],
                        "packages_protected": ["kept-tool"],
                    },
                    "tasks": [
                        {
                            "ansible.builtin.include_tasks": str(
                                ROLES / "packages/tasks/reconcile.yml"
                            )
                        },
                        {
                            "ansible.builtin.assert": {
                                "that": "packages_removal_candidates == ['old-tool']"
                            }
                        },
                    ],
                }
            ],
            "--check",
        )
        self.assertIn("All assertions passed", output)

    # A fresh clone has no .vault file and must still run.
    def test_repository_config_does_not_require_a_vault_password_file(self):
        config = self.work / "ansible.cfg"
        shutil.copy(ROOT / "ansible.cfg", config)
        playbook = self.work / "noop.yml"
        playbook.write_text(
            yaml.safe_dump([{"hosts": "localhost", "gather_facts": False, "tasks": []}])
        )
        result = subprocess.run(
            ["ansible-playbook", "-i", "localhost,", str(playbook)],
            cwd=self.work,
            env={**os.environ, "ANSIBLE_CONFIG": str(config)},
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_make_passes_the_vault_password_file_only_when_present(self):
        shutil.copy(ROOT / "Makefile", self.work / "Makefile")

        def dry_run(target):
            return subprocess.run(
                ["make", "-n", target],
                cwd=self.work,
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            ).stdout

        for target in ["install", "ansible-backup-ls", "ansible-backup-rm"]:
            self.assertNotIn("ANSIBLE_VAULT_PASSWORD_FILE", dry_run(target))
        (self.work / ".vault").write_text("secret\n")
        for target in ["install", "ansible-backup-ls", "ansible-backup-rm"]:
            self.assertIn(
                f'ANSIBLE_VAULT_PASSWORD_FILE="{self.work}/.vault"', dry_run(target)
            )

    def render_hardening(self, groups, ipv6_enabled=True):
        template = ROLES / "hardening/templates/hardening.conf.j2"
        output = self.work / "hardening.conf"
        self.run_play(
            [
                {
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "ansible_facts": {"hostname": "fixture"},
                        "hardening_ipv6_enabled": ipv6_enabled,
                        "hardening_optional_sysctls": {
                            "results": [{"stat": {"exists": False}}] * 4
                        },
                        "packages_selected_groups": groups,
                    },
                    "tasks": [
                        {
                            "ansible.builtin.template": {
                                "src": str(template),
                                "dest": str(output),
                                "mode": "0644",
                            }
                        }
                    ],
                }
            ]
        )
        return output.read_text()

    def test_ipv4_forwarding_follows_container_groups(self):
        for groups, expected in [
            (["01_base"], "net.ipv4.ip_forward = 0"),
            (["01_base", "12_containers_docker"], "net.ipv4.ip_forward = 1"),
            (["13_containers_podman"], "net.ipv4.ip_forward = 1"),
        ]:
            with self.subTest(groups=groups):
                self.assertIn(expected, self.render_hardening(groups))

    def test_ipv6_follows_the_host_switch(self):
        for enabled, expected in [(True, "0"), (False, "1")]:
            with self.subTest(enabled=enabled):
                policy = self.render_hardening(["01_base"], ipv6_enabled=enabled)
                self.assertIn(f"net.ipv6.conf.all.disable_ipv6 = {expected}", policy)
                self.assertIn(
                    f"net.ipv6.conf.default.disable_ipv6 = {expected}", policy
                )

    # The former hostname map must fail loudly instead of selecting its keys.
    @unittest.skipUnless(COLLECTIONS.is_dir(), "requires pinned Ansible collections")
    def test_package_role_rejects_a_hostname_map_of_groups(self):
        output = self.run_play(
            self.package_role_play(packages_host_groups={"PadsTower": ["01_base"]}),
            "--check",
            expect_success=False,
        )
        self.assertIn("packages_host_groups takes a list of package groups", output)
        self.assertNotIn(MARKER, output)

    @unittest.skipUnless(COLLECTIONS.is_dir(), "requires pinned Ansible collections")
    def test_system_tags_load_the_package_group_selection(self):
        environment = {
            **os.environ,
            "ANSIBLE_CONFIG": str(ROOT / "ansible.cfg"),
            "ANSIBLE_LOCAL_TEMP": str(self.work / "ansible-local"),
        }
        for tag in ["system", "kernel_hardening", "dns", "gpu_modules", "obs"]:
            with self.subTest(tag=tag):
                result = subprocess.run(
                    [
                        "ansible-playbook",
                        "ansible/site.yml",
                        "--list-tasks",
                        "--tags",
                        tag,
                    ],
                    cwd=ROOT,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                # The selection is an include, so --list-tasks shows its entry.
                self.assertIn("Select the package groups of this host", result.stdout)

    # gaming.yml uses community.general.pacman, resolved even when skipped.
    @unittest.skipUnless(COLLECTIONS.is_dir(), "requires pinned Ansible collections")
    def test_gaming_check_mode_reports_missing_packages_instead_of_failing(self):
        output = self.run_play(
            [
                {
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "packages_gaming_required_packages": [
                            "dotfiles-test-package-that-does-not-exist"
                        ],
                        "cpu_power_managers": [],
                    },
                    "tasks": [
                        {
                            "ansible.builtin.include_tasks": str(
                                ROLES / "gaming/tasks/main.yml"
                            )
                        },
                        {"ansible.builtin.debug": {"msg": MARKER}},
                    ],
                }
            ],
            "--check",
        )
        self.assertIn("dotfiles-test-package-that-does-not-exist", output)
        self.assertIn(MARKER, output)

    @unittest.skipUnless(COLLECTIONS.is_dir(), "requires pinned Ansible collections")
    def test_gaming_still_requires_packages_outside_check_mode(self):
        output = self.run_play(
            [
                {
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "packages_gaming_required_packages": [
                            "dotfiles-test-package-that-does-not-exist"
                        ],
                    },
                    "tasks": [
                        {
                            "ansible.builtin.include_tasks": str(
                                ROLES / "gaming/tasks/main.yml"
                            )
                        }
                    ],
                }
            ],
            expect_success=False,
        )
        self.assertIn("Install the complete 21_steam group", output)

    def run_amd_persistence(self, **extra_vars):
        destination = self.work / "tmpfiles.d/dotfiles-amd-cpu.conf"
        destination.parent.mkdir(exist_ok=True)
        tasks = yaml.safe_load(
            (ROLES / "cpu_power/tasks/amd_persistence.yml").read_text()
        )
        for task in tasks:
            for module in ("ansible.builtin.template", "ansible.builtin.file"):
                if module in task:
                    task[module].pop("owner", None)
                    task[module].pop("group", None)
                    if module == "ansible.builtin.template":
                        task[module]["src"] = str(
                            ROLES / "cpu_power/templates" / task[module]["src"]
                        )
        self.run_play(
            [
                {
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "cpu_power_amd_tmpfiles_path": str(destination),
                        "cpu_power_amd_pstate_epp": "balance_performance",
                        "cpu_power_amd_x3d_mode": None,
                        **extra_vars,
                    },
                    "tasks": tasks,
                }
            ]
        )
        return destination

    def test_amd_controls_are_persisted_in_governor_then_epp_order(self):
        destination = self.run_amd_persistence(
            cpu_power_amd_epp_files={"files": [{"path": "/sys/policy0/epp"}]},
            cpu_power_amd_x3d_mode="cache",
            cpu_power_amd_x3d_controls={"files": [{"path": "/sys/x3d/amd_x3d_mode"}]},
        )
        lines = [
            line
            for line in destination.read_text().splitlines()
            if line.startswith("w ")
        ]
        self.assertEqual(
            lines,
            [
                "w /sys/devices/system/cpu/cpufreq/policy*/scaling_governor"
                " - - - - powersave",
                "w /sys/devices/system/cpu/cpufreq/policy*/"
                "energy_performance_preference - - - - balance_performance",
                "w /sys/bus/platform/drivers/amd_x3d_vcache/*/amd_x3d_mode"
                " - - - - cache",
            ],
        )

    def test_amd_persistence_is_removed_when_nothing_is_managed(self):
        destination = self.run_amd_persistence(
            cpu_power_amd_epp_files={"files": [{"path": "/sys/policy0/epp"}]}
        )
        self.assertTrue(destination.exists())
        # A power manager now owns EPP, so discovery is skipped.
        destination = self.run_amd_persistence(
            cpu_power_amd_epp_files={"skipped": True}
        )
        self.assertFalse(destination.exists())

    def test_missing_arch_packages_honour_provides(self):
        tasks = yaml.safe_load((ROLES / "packages/tasks/install.yml").read_text())
        names = [
            "Find desired packages unsatisfied on Arch Linux",
            "Find missing desired packages",
        ]
        selected = [task for task in tasks if task["name"] in names]
        self.assertEqual(len(selected), 2)
        binary = self.work / "bin"
        binary.mkdir()
        pacman = binary / "pacman"
        # Simulate pacman -T: foo is provided by an installed foo-git package.
        pacman.write_text(
            "#!/bin/sh\n"
            'test "$1" = -T || exit 2\n'
            "shift\n"
            'test "$1" = -- && shift\n'
            "status=0\n"
            'for name in "$@"; do\n'
            '  if [ "$name" != foo ]; then echo "$name"; status=127; fi\n'
            "done\n"
            "exit $status\n"
        )
        pacman.chmod(0o755)
        output = self.run_play(
            [
                {
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "environment": {
                        "PATH": f"{binary}:{os.environ['PATH']}",
                    },
                    "vars": {
                        "ansible_facts": {"os_family": "Archlinux"},
                        "packages_selected_groups": ["01_base"],
                        "packages_desired": ["bar", "foo"],
                        "packages_installed_before": ["foo-git"],
                    },
                    "tasks": selected
                    + [
                        {
                            "ansible.builtin.assert": {
                                "that": "packages_missing == ['bar']"
                            }
                        }
                    ],
                }
            ],
            "--check",
        )
        self.assertIn("All assertions passed", output)

    def test_conflicting_symlinks_are_backed_up_not_deleted(self):
        role = self.work / "dotfiles"
        shutil.copytree(ROLES / "dotfiles", role, symlinks=True)
        handlers = yaml.safe_load((role / "handlers/main.yml").read_text())
        (role / "handlers/main.yml").write_text(
            yaml.safe_dump(
                [
                    {"name": h["name"], "ansible.builtin.debug": {"msg": h["name"]}}
                    for h in handlers
                ]
            )
        )
        home = self.work / "home"
        home.mkdir()
        elsewhere = self.work / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "gitconfig").write_text("local\n")
        (home / ".gitconfig").symlink_to(elsewhere / "gitconfig")
        (home / ".vim").symlink_to(elsewhere)
        play = [
            {
                "hosts": "localhost",
                "connection": "local",
                "gather_facts": False,
                "vars": {
                    "dotfiles_home": str(home),
                    "dotfiles_repository": str(ROOT),
                    "dotfiles_directories": [],
                    "dotfiles_files": [".gitconfig"],
                    "dotfiles_links": [{"src": ".vim", "dest": ".vim"}],
                    "dotfiles_templates": [],
                    "dotfiles_systemd_graphical_units": [],
                    "dotfiles_systemd_directory": ".config/test-systemd",
                    "dotfiles_waybar_host_config": "config.fixture",
                },
                "tasks": [
                    {
                        "ansible.builtin.import_role": {
                            "name": str(role),
                            "tasks_from": "deploy",
                        },
                        "tags": ["dotfiles_deploy"],
                    }
                ],
            }
        ]
        (role / "files/home/.config/test-systemd/user").mkdir(parents=True)
        self.run_play(play, "--tags", "dotfiles_deploy")
        self.assertEqual(
            os.readlink(home / ".gitconfig.bak"), str(elsewhere / "gitconfig")
        )
        self.assertFalse((home / ".gitconfig").is_symlink())
        self.assertEqual(
            (home / ".gitconfig").read_text(),
            (role / "files/home/.gitconfig").read_text(),
        )
        self.assertEqual(os.readlink(home / ".vim.bak"), str(elsewhere))
        self.assertEqual(os.readlink(home / ".vim"), str(role / "files/home/.vim"))
        self.assertEqual((elsewhere / "gitconfig").read_text(), "local\n")

    # Skipping these reads in check mode silently dropped vm.mmap_rnd_bits.
    def test_sysctl_reads_run_in_check_mode(self):
        tasks = [
            task
            for task in yaml.safe_load(
                (ROLES / "hardening/tasks/kernel_hardening.yml").read_text()
            )
            if task["name"].startswith("Read the active")
        ]
        self.assertEqual(len(tasks), 2)
        binary = self.work / "bin"
        binary.mkdir()
        sysctl = binary / "sysctl"
        sysctl.write_text("#!/bin/sh\necho 32\n")
        sysctl.chmod(0o755)
        output = self.run_play(
            [
                {
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "environment": {"PATH": f"{binary}:{os.environ['PATH']}"},
                    "vars": {
                        "hardening_optional_sysctls": {
                            "results": [{"stat": {"exists": True}}] * 4
                        }
                    },
                    "tasks": tasks
                    + [
                        {
                            "ansible.builtin.assert": {
                                "that": [
                                    "hardening_mmap_rnd_bits.stdout == '32'",
                                    "hardening_unprivileged_bpf_disabled.stdout == '32'",
                                ]
                            }
                        }
                    ],
                }
            ],
            "--check",
        )
        self.assertIn("All assertions passed", output)

    def stub_handlers(self, handlers_file):
        """Replace real handlers with debug tasks that print their own name."""
        handlers = yaml.safe_load(handlers_file.read_text())
        return [
            {
                "name": handler["name"],
                "ansible.builtin.debug": {"msg": f"HANDLER {handler['name']}"},
            }
            for handler in handlers
        ]

    def test_config_changes_notify_the_matching_reload_handlers(self):
        role = self.work / "dotfiles"
        shutil.copytree(ROLES / "dotfiles", role, symlinks=True)
        (role / "handlers/main.yml").write_text(
            yaml.safe_dump(self.stub_handlers(role / "handlers/main.yml"))
        )
        source = self.work / "source"
        for name in [
            ".config/hypr/hypridle.conf",
            ".config/hypr/config.lua",
            ".config/xdg-desktop-portal/hyprland-portals.conf",
            ".config/uwsm/env",
        ]:
            (source / name).parent.mkdir(parents=True, exist_ok=True)
            (source / name).write_text("one\n")
        play = [
            {
                "hosts": "localhost",
                "connection": "local",
                "gather_facts": False,
                "vars": {
                    "dotfiles_home": str(self.work / "home"),
                    "dotfiles_source_root": str(source),
                },
                "tasks": [
                    {
                        "ansible.builtin.include_tasks": {
                            "file": str(role / "tasks/copy-directory.yml"),
                        },
                        "loop": [
                            ".config/hypr",
                            ".config/xdg-desktop-portal",
                            ".config/uwsm",
                        ],
                        "loop_control": {"loop_var": "dotfiles_directory"},
                    }
                ],
                "handlers": yaml.safe_load((role / "handlers/main.yml").read_text()),
            }
        ]
        play[0]["vars"].update(yaml.safe_load((role / "defaults/main.yml").read_text()))
        play[0]["vars"]["dotfiles_home"] = str(self.work / "home")
        play[0]["vars"]["dotfiles_source_root"] = str(source)
        # Each handler prints "HANDLER <name>" once when it runs.
        first = self.run_play(play)
        for handler in [
            "Restart hypridle",
            "Restart Hyprlauncher",
            "Restart XDG desktop portal",
            "Report session restart required",
        ]:
            self.assertIn(f"HANDLER {handler}", first)
        self.assertNotIn("HANDLER ", self.run_play(play))
        (source / ".config/hypr/config.lua").write_text("two\n")
        output = self.run_play(play)
        self.assertIn("HANDLER Restart Hyprlauncher", output)
        self.assertNotIn("HANDLER Restart hypridle", output)
        (source / ".config/hypr/hypridle.conf").write_text("two\n")
        self.assertIn("HANDLER Restart hypridle", self.run_play(play))

    def test_runtime_pm_rule_changes_reload_udev(self):
        tasks = [
            task
            for task in yaml.safe_load((ROLES / "gpu/tasks/runtime_pm.yml").read_text())
            if "80-dotfiles-nvidia-runtime-pm.rules" in yaml.safe_dump(task)
        ]
        self.assertEqual(len(tasks), 2)
        rule = self.work / "80-dotfiles-nvidia-runtime-pm.rules"
        for task in tasks:
            for module in ("ansible.builtin.copy", "ansible.builtin.file"):
                if module in task:
                    task[module].pop("owner", None)
                    task[module].pop("group", None)
                    task[module]["dest" if module.endswith("copy") else "path"] = str(
                        rule
                    )
                    if module.endswith("copy"):
                        task[module]["src"] = str(
                            ROLES / "gpu/files" / task[module]["src"]
                        )

        def run(detection):
            return self.run_play(
                [
                    {
                        "hosts": "localhost",
                        "connection": "local",
                        "gather_facts": False,
                        "vars": {
                            "packages_selected_groups": ["09_nvidia_modern"],
                            "gpu_hybrid_laptop_detection": {"stdout": detection},
                        },
                        "tasks": tasks,
                        "handlers": self.stub_handlers(ROLES / "gpu/handlers/main.yml"),
                    }
                ]
            )

        installed = run("true")
        self.assertTrue(rule.exists())
        self.assertIn("HANDLER Reload udev rules", installed)
        self.assertIn("HANDLER Apply NVIDIA runtime PM udev rule", installed)
        self.assertNotIn("HANDLER ", run("true"))
        removed = run("false")
        self.assertFalse(rule.exists())
        self.assertIn("HANDLER Reload udev rules", removed)
        self.assertIn("HANDLER Report NVIDIA runtime PM kept until reboot", removed)

    def test_removed_legacy_sysctl_files_report_a_reboot(self):
        sysctl_dir = self.work / "sysctl.d"
        sysctl_dir.mkdir()
        (sysctl_dir / "80-gamecompatibility.conf").write_text("vm.x = 1\n")
        all_tasks = yaml.safe_load(
            (ROLES / "hardening/tasks/kernel_hardening.yml").read_text()
        )
        names = [
            "Check for legacy gaming sysctl drop-ins",
            "Back up legacy gaming sysctl files",
            "Remove legacy gaming sysctl files",
        ]
        tasks = yaml.safe_load(
            yaml.safe_dump([t for t in all_tasks if t["name"] in names]).replace(
                "/etc/sysctl.d", str(sysctl_dir)
            )
        )
        for task in tasks:
            if "ansible.builtin.copy" in task:
                task["ansible.builtin.copy"].pop("owner", None)
                task["ansible.builtin.copy"].pop("group", None)
        play = [
            {
                "hosts": "localhost",
                "connection": "local",
                "gather_facts": False,
                "tasks": tasks,
                "handlers": self.stub_handlers(ROLES / "hardening/handlers/main.yml"),
            }
        ]
        output = self.run_play(play)
        self.assertIn("HANDLER Report legacy sysctl values kept until reboot", output)
        self.assertFalse((sysctl_dir / "80-gamecompatibility.conf").exists())
        self.assertNotIn("HANDLER ", self.run_play(play))

    def run_package_services(self, groups, units, expect_success=True, **extra_vars):
        unit_directory = self.work / "units"
        unit_directory.mkdir(exist_ok=True)
        for unit in units:
            (unit_directory / unit).write_text("[Unit]\n")
        tasks = yaml.safe_load((ROLES / "package_services/tasks/main.yml").read_text())
        # Stop before systemd and account changes; only the selection is tested.
        stop = next(
            index
            for index, task in enumerate(tasks)
            if task["name"] == "Enable and start services for the selected packages"
        )
        tasks = tasks[:stop]
        defaults = yaml.safe_load(
            (ROLES / "package_services/defaults/main.yml").read_text()
        )
        return self.run_play(
            [
                {
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "ansible_facts": {"os_family": "Archlinux"},
                        "package_services_by_group": defaults[
                            "package_services_by_group"
                        ],
                        "package_services_unit_directory": str(unit_directory),
                        "packages_selected_groups": groups,
                        **extra_vars,
                    },
                    "tasks": tasks
                    + [
                        {
                            "ansible.builtin.debug": {
                                "msg": "ENABLE {{ package_services_to_enable }}"
                            }
                        }
                    ],
                }
            ],
            expect_success=expect_success,
        )

    def test_selected_groups_enable_their_installed_services(self):
        output = self.run_package_services(
            ["01_base", "04_printers", "12_containers_docker"],
            ["bluetooth.service", "cups.socket", "docker.socket", "paccache.timer"],
        )
        self.assertIn(
            "ENABLE ['bluetooth.service', 'cups.socket', 'docker.socket']", output
        )
        # paccache.timer is installed but deliberately not managed.
        self.assertNotIn("paccache.timer", output)
        self.assertNotIn("fwupd-refresh.timer", output)

    def test_services_without_unit_files_are_reported_not_enabled(self):
        output = self.run_package_services(["20_apps", "04_printers"], ["cups.socket"])
        self.assertIn("ENABLE ['cups.socket']", output)
        self.assertIn("unit file is missing: fwupd-refresh.timer", output)

    def test_conflicting_power_managers_are_removed_only_when_accepted(self):
        tasks = yaml.safe_load((ROLES / "gaming/tasks/main.yml").read_text())
        block = next(task for task in tasks if "block" in task)["block"]
        decide = next(t for t in block if t["name"].startswith("Decide whether"))
        conflict = ["auto-cpufreq.service"]

        def decision(action, answer=None, conflicts=conflict, check=False):
            facts = {
                "gaming_conflicting_power_managers": conflicts,
                "gaming_power_manager_conflict_action": action,
            }
            if answer is not None:
                facts["gaming_power_manager_prompt"] = {"user_input": answer}
            output = self.run_play(
                [
                    {
                        "hosts": "localhost",
                        "connection": "local",
                        "gather_facts": False,
                        "vars": facts,
                        "tasks": [
                            decide,
                            {
                                "ansible.builtin.debug": {
                                    "msg": "REMOVE={{ gaming_remove_power_managers"
                                    " | bool }}"
                                },
                                "check_mode": False,
                            },
                        ],
                    }
                ],
                *(["--check"] if check else []),
            )
            return "REMOVE=True" in output

        cases = [
            (("ask", " Yes "), True),
            (("ask", "y"), True),
            (("ask", ""), False),
            (("ask", "n"), False),
            (("ask",), False),
            (("remove",), True),
            (("fail", "y"), False),
        ]
        for arguments, expected in cases:
            with self.subTest(arguments=arguments):
                self.assertEqual(decision(*arguments), expected)
        self.assertFalse(decision("remove", conflicts=[]))
        self.assertFalse(decision("remove", check=True))

    def test_ananicy_restarts_only_when_its_rules_package_changed(self):
        tasks = yaml.safe_load((ROLES / "gaming/tasks/main.yml").read_text())
        block = next(task for task in tasks if "block" in task)["block"]
        task = next(t for t in block if t["name"].startswith("Restart ananicy-cpp"))
        task = {
            "name": task["name"],
            "when": task["when"],
            "ansible.builtin.debug": {"msg": "ANANICY RESTART"},
        }
        defaults = yaml.safe_load((ROLES / "gaming/defaults/main.yml").read_text())

        def run(changed):
            return self.run_play(
                [
                    {
                        "hosts": "localhost",
                        "connection": "local",
                        "gather_facts": False,
                        "vars": {
                            "packages_changed_this_run": changed,
                            "gaming_ananicy_rule_packages": defaults[
                                "gaming_ananicy_rule_packages"
                            ],
                        },
                        "tasks": [task],
                    }
                ]
            )

        self.assertIn("ANANICY RESTART", run(["cachyos-ananicy-rules"]))
        self.assertNotIn("ANANICY RESTART", run(["jq"]))

    # Without a before snapshot nothing may count as changed, or every run
    # would restart services that react to package changes.
    def test_package_changes_need_a_before_snapshot(self):
        task = next(
            task
            for task in yaml.safe_load((ROLES / "packages/tasks/apply.yml").read_text())
            if task["name"] == "Snapshot installed packages after installation"
        )
        task.pop("when", None)
        task.pop("tags", None)
        packages = {"jq": [{"version": "1.7", "release": "1", "arch": "x86_64"}]}
        play = {
            "hosts": "localhost",
            "connection": "local",
            "gather_facts": False,
            "vars": {"ansible_facts": {"packages": packages}},
            "tasks": [
                task,
                {
                    "ansible.builtin.assert": {
                        "that": "packages_changed_this_run == expected"
                    }
                },
            ],
        }
        self.run_play([{**play, "vars": {**play["vars"], "expected": []}}])
        self.run_play(
            [
                {
                    **play,
                    "vars": {
                        **play["vars"],
                        "packages_facts_before": {},
                        "expected": ["jq"],
                    },
                }
            ]
        )


if __name__ == "__main__":
    unittest.main()
