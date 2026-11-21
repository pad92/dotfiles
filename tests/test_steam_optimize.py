import json
import os
import re
import runpy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SCRIPT_PATH = (
    Path(__file__).parents[1] / "ansible/roles/dotfiles/files/home/.bin/steam-optimize"
)

HYPR_WINDOW_RULES = (
    Path(__file__).parents[1]
    / "ansible/roles/dotfiles/files/home/.config/hypr/conf/windowrules.lua"
)


# hyprctl -j replies modelled on PadsTower: Dell on DP-2, ASUS on DP-3.
MONITORS = [
    {
        "name": "DP-2",
        "description": "Dell Inc. DELL P2423DE 3PJ4CN3",
        "width": 2560,
        "height": 1440,
        "refreshRate": 59.95,
        "activeWorkspace": {"id": 2},
    },
    {
        "name": "DP-3",
        "description": "ASUSTek COMPUTER INC XG32WCS TALMAS012758",
        "width": 3840,
        "height": 2160,
        "refreshRate": 143.9,
        "activeWorkspace": {"id": 5},
    },
]
WORKSPACE_RULES = [
    {"workspaceString": "1", "monitor": "desc:ASUSTek COMPUTER INC XG32WCS"},
    {"workspaceString": "2", "monitor": "desc:Dell Inc. DELL P2423DE"},
]


class SteamOptimizeTests(unittest.TestCase):
    def setUp(self):
        self.script = runpy.run_path(str(SCRIPT_PATH), run_name="steam_optimize")

    def test_arch_launch_does_not_require_cachyos_game_performance(self):
        launch = self.script["build_launch_command"](["game", "--fullscreen"], None)

        self.assertEqual(
            launch,
            [
                "systemd-inhibit",
                "--what=idle",
                "--who=steam-optimize",
                "--why=Steam game running",
                "game",
                "--fullscreen",
            ],
        )

    def test_cachyos_launch_uses_game_performance(self):
        launch = self.script["build_launch_command"](
            ["game"], "/usr/bin/game-performance"
        )

        self.assertEqual(launch[4:], ["/usr/bin/game-performance", "game"])

    def test_active_localconfig_converts_steam_id_to_account_id(self):
        account_id = 1234
        steam_id = 76561197960265728 + account_id

        class FakeVdf:
            @staticmethod
            def load(_file):
                return {
                    "users": {
                        str(steam_id): {"MostRecent": "1"},
                        "76561197960271394": {"MostRecent": "0"},
                    }
                }

        with tempfile.TemporaryDirectory() as temporary_directory:
            steam_root = Path(temporary_directory)
            (steam_root / "config").mkdir()
            (steam_root / "config" / "loginusers.vdf").touch()

            expected = (
                steam_root / "userdata" / str(account_id) / "config" / "localconfig.vdf"
            )
            expected.parent.mkdir(parents=True)
            expected.touch()

            other = steam_root / "userdata" / "9999" / "config" / "localconfig.vdf"
            other.parent.mkdir(parents=True)
            other.touch()

            result = self.script["find_active_localconfig_path"](
                str(steam_root), FakeVdf
            )

        self.assertEqual(result, str(expected))

    def test_active_localconfig_without_loginusers(self):
        for account_ids in [[], ["1234"], ["1234", "9999"]]:
            with (
                self.subTest(account_ids=account_ids),
                tempfile.TemporaryDirectory() as directory,
            ):
                steam_root = Path(directory)
                paths = []
                for account_id in account_ids:
                    path = (
                        steam_root
                        / "userdata"
                        / account_id
                        / "config"
                        / "localconfig.vdf"
                    )
                    path.parent.mkdir(parents=True)
                    path.touch()
                    paths.append(str(path))

                result = self.script["find_active_localconfig_path"](
                    str(steam_root), SimpleNamespace()
                )

                self.assertEqual(result, paths[0] if len(paths) == 1 else None)

    def test_hybrid_gpu_uses_only_nvidia_specific_environment(self):
        original_isdir = os.path.isdir

        def module_isdir(path):
            if path in ("/sys/module/amdgpu", "/sys/module/nvidia"):
                return True
            return original_isdir(path)

        self.script["check_gamescope_supports_output"] = lambda: True
        self.script["log_info"] = lambda _message: None
        self.script["log_warn"] = lambda _message: None

        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch("os.path.isdir", side_effect=module_isdir),
        ):
            self.script["setup_global_env"]()
            environment = dict(os.environ)

        self.assertEqual(environment["__NV_PRIME_RENDER_OFFLOAD"], "1")
        self.assertNotIn("AMD_VULKAN_ICD", environment)
        self.assertNotIn("RADV_PERFTEST", environment)

    def test_gta_enhanced_sets_only_the_battleye_runtime_proton_reads(self):
        failed = SimpleNamespace(returncode=1, stdout="")
        with (
            mock.patch.dict(os.environ, {"HOME": "/home/player"}, clear=True),
            mock.patch("subprocess.run", return_value=failed),
            mock.patch("os.path.isdir", return_value=False),
        ):
            name, _cmd, _profile = self.script["apply_game_overrides"](
                "3240220", ["game"]
            )
            battleye_variables = {
                key: value
                for key, value in os.environ.items()
                if key.startswith("PROTON_BATTLEYE")
            }

        self.assertEqual(name, "Grand Theft Auto V Enhanced")
        self.assertEqual(
            battleye_variables,
            {
                "PROTON_BATTLEYE_RUNTIME": "/home/player/.local/share/Steam"
                "/steamapps/common/Proton BattlEye Runtime"
            },
        )

    def test_hyprland_keeps_valid_inherited_session(self):
        expected_path = "/run/user/1000/hypr/current-session"

        def isdir(path):
            return path in ("/run/user/1000/hypr", expected_path)

        with (
            mock.patch.dict(
                os.environ,
                {"HYPRLAND_INSTANCE_SIGNATURE": "current-session"},
                clear=True,
            ),
            mock.patch("os.getuid", return_value=1000),
            mock.patch("os.path.isdir", side_effect=isdir),
            mock.patch("os.listdir", side_effect=AssertionError("must not rescan")),
        ):
            self.script["setup_hyprland_env"]()
            selected_session = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")

        self.assertEqual(selected_session, "current-session")

    def gamescope_args_with(self, workspaces, **kwargs):
        replies = {
            "monitors": MONITORS,
            "workspaces": workspaces,
            "workspacerules": WORKSPACE_RULES,
        }

        def run(command, **_kwargs):
            return SimpleNamespace(returncode=0, stdout=json.dumps(replies[command[1]]))

        self.script["log_warn"] = lambda _message: None
        with (
            mock.patch.dict(
                os.environ, {"HYPRLAND_INSTANCE_SIGNATURE": "session"}, clear=True
            ),
            mock.patch("subprocess.run", side_effect=run),
        ):
            return self.script["get_gamescope_args"]("workspace:1", True, **kwargs)

    def test_workspace_selector_uses_rule_monitor_when_workspace_is_hidden(self):
        # Workspace 1 does not exist and the ASUS shows workspace 5: the rule
        # still places workspace 1, and the game window, on the ASUS.
        args = self.gamescope_args_with(
            [{"id": 2, "monitor": "DP-2"}, {"id": 5, "monitor": "DP-3"}]
        )

        self.assertEqual(args[:4], ["-W", "3840", "-H", "2160"])
        self.assertEqual(args[-4:], ["-r", "144", "-O", "DP-3"])

    def test_gamescope_does_not_force_the_cursor_grab_by_default(self):
        # Forcing the grab trapped the pointer in menus and windowed mode;
        # Hyprland confines it only while the game window is fullscreen.
        args = self.gamescope_args_with([{"id": 1, "monitor": "DP-2"}])

        self.assertIn("-f", args)
        self.assertNotIn("--force-grab-cursor", args)

    def test_profile_can_force_the_gamescope_cursor_grab(self):
        args = self.gamescope_args_with(
            [{"id": 1, "monitor": "DP-2"}], grab_cursor=True
        )

        self.assertIn("--force-grab-cursor", args)

    def test_workspace_selector_follows_an_existing_workspace(self):
        args = self.gamescope_args_with(
            [{"id": 1, "monitor": "DP-2"}, {"id": 5, "monitor": "DP-3"}]
        )

        self.assertEqual(args[-2:], ["-O", "DP-2"])

    def test_mouse_dpi_ignores_numbers_in_diagnostic_text(self):
        output = "Device Razer Viper 8K has no DPI setter\n1600\n"
        result = SimpleNamespace(returncode=0, stdout=output)

        with mock.patch("subprocess.run", return_value=result):
            dpi = self.script["get_current_mouse_dpi"]()

        self.assertEqual(dpi, 1600)

    def parse_args_with(self, *args):
        with (
            mock.patch("sys.argv", ["steam-optimize", *args]),
            mock.patch("subprocess.run") as run,
        ):
            parsed = self.script["parse_args"]()
        return parsed, run

    def test_dpi_option_is_parsed_for_the_launch(self):
        parsed, _run = self.parse_args_with("--dpi", "800", "--", "game")

        self.assertEqual(parsed[-2:], (800, ["game"]))

    def test_invalid_dpi_is_ignored_without_blocking_the_game(self):
        for value in ("abc", "0", "999999"):
            with self.subTest(value=value):
                parsed, _run = self.parse_args_with("--dpi", value, "--", "game")

                self.assertEqual(parsed[-2:], (None, ["game"]))

    def test_missing_dpi_value_keeps_the_game_command(self):
        parsed, _run = self.parse_args_with("--dpi", "--", "game", "-flag")

        self.assertEqual(parsed[-2:], (None, ["game", "-flag"]))

    def test_mouse_dpi_is_skipped_when_razer_cli_is_missing(self):
        with (
            mock.patch("shutil.which", return_value=None),
            mock.patch("subprocess.run") as run,
        ):
            self.script["apply_mouse_dpi"](800)

        razer_calls = [
            call for call in run.call_args_list if call.args[0][0] == "razer-cli"
        ]
        self.assertEqual(razer_calls, [])
        self.assertFalse(self.script["apply_mouse_dpi"].__globals__["_dpi_changed"])

    def test_game_profiles_never_change_the_mouse_dpi(self):
        failed = SimpleNamespace(returncode=1, stdout="")
        with (
            mock.patch.dict(os.environ, {"HOME": "/home/player"}, clear=True),
            mock.patch("subprocess.run", return_value=failed) as run,
            mock.patch("os.path.isdir", return_value=False),
        ):
            for appid in self.script["GAME_PROFILES"]:
                self.script["apply_game_overrides"](appid, ["game"])

        commands = [call.args[0][0] for call in run.call_args_list]
        self.assertNotIn("razer-cli", commands)

    def test_managed_launch_option_round_trips(self):
        launch_cls = self.script["ManagedLaunch"]
        build = self.script["build_managed_option"]
        parse = self.script["parse_managed_option"]
        script_path = "/home/player/.bin/steam-optimize"

        for launch in (
            launch_cls(),
            launch_cls(mangohud=True),
            launch_cls(dpi=800),
            launch_cls(mangohud=True, dpi=1600),
        ):
            with self.subTest(launch=launch):
                self.assertEqual(parse(build(script_path, launch), script_path), launch)

        self.assertEqual(
            build(script_path, launch_cls(mangohud=True)),
            f"{script_path} --mangohud -- %command%",
        )

    def test_custom_launch_options_are_not_managed(self):
        parse = self.script["parse_managed_option"]
        script_path = "/home/player/.bin/steam-optimize"

        for option in (
            "gamemoderun %command%",
            f"{script_path} --monitor DP-1 -- %command%",
            f"{script_path} --dpi 5 -- %command%",
            f"{script_path} --dpi 800 --dpi 900 -- %command%",
            f"{script_path} --dpi -- %command%",
            f"{script_path} -- %command% -novid",
        ):
            with self.subTest(option=option):
                self.assertIsNone(parse(option, script_path))

    def test_toggle_keeps_the_dpi_until_disabled(self):
        launch_cls = self.script["ManagedLaunch"]
        toggle = self.script["next_toggle_state"]

        enabled = toggle(launch_cls(dpi=800))

        self.assertEqual(enabled, launch_cls(mangohud=True, dpi=800))
        self.assertIsNone(toggle(enabled))
        self.assertEqual(toggle(None), launch_cls())

    def test_disable_all_leaves_custom_launch_options(self):
        config = {
            "UserLocalConfigStore": {
                "Software": {
                    "Valve": {
                        "Steam": {
                            "apps": {
                                "1": {"LaunchOptions": "managed"},
                                "2": {"LaunchOptions": "custom"},
                            }
                        }
                    }
                }
            }
        }
        set_launch_option = self.script["set_launch_option"]

        for appid in ("1", "2"):
            set_launch_option([config], appid, None, lambda o: o == "managed")

        apps = config["UserLocalConfigStore"]["Software"]["Valve"]["Steam"]["apps"]
        self.assertEqual(apps, {"1": {}, "2": {"LaunchOptions": "custom"}})


class GameWindowRuleTests(unittest.TestCase):
    def test_pointer_is_confined_only_to_fullscreen_game_windows(self):
        rules = re.findall(
            r"hl\.window_rule\(\{.*?\}\)",
            HYPR_WINDOW_RULES.read_text(encoding="utf-8"),
            re.DOTALL,
        )
        confining = [rule for rule in rules if "confine_pointer" in rule]

        self.assertEqual(len(confining), 1)
        self.assertIn("gamescope|steam_app_", confining[0])
        self.assertRegex(confining[0], r"match\s*=\s*\{[^}]*fullscreen\s*=\s*true")


if __name__ == "__main__":
    unittest.main()
