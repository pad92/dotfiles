import json
import os
import runpy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SCRIPT_PATH = (
    Path(__file__).parents[1] / "ansible/roles/dotfiles/files/home/.bin/steam-optimize"
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
            with self.subTest(
                account_ids=account_ids
            ), tempfile.TemporaryDirectory() as directory:
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

    def gamescope_args_with(self, workspaces):
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
            return self.script["get_gamescope_args"]("workspace:1", True)

    def test_workspace_selector_uses_rule_monitor_when_workspace_is_hidden(self):
        # Workspace 1 does not exist and the ASUS shows workspace 5: the rule
        # still places workspace 1, and the game window, on the ASUS.
        args = self.gamescope_args_with(
            [{"id": 2, "monitor": "DP-2"}, {"id": 5, "monitor": "DP-3"}]
        )

        self.assertEqual(args[:4], ["-W", "3840", "-H", "2160"])
        self.assertEqual(args[-4:], ["-r", "144", "-O", "DP-3"])

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


if __name__ == "__main__":
    unittest.main()
