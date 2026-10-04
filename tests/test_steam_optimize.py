import os
import runpy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SCRIPT_PATH = Path(__file__).parents[1] / "bin" / "steam-optimize"


class SteamOptimizeTests(unittest.TestCase):
    def setUp(self):
        self.script = runpy.run_path(str(SCRIPT_PATH), run_name="steam_optimize")

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

    def test_mouse_dpi_ignores_numbers_in_diagnostic_text(self):
        output = "Device Razer Viper 8K has no DPI setter\n1600\n"
        result = SimpleNamespace(returncode=0, stdout=output)

        with mock.patch("subprocess.run", return_value=result):
            dpi = self.script["get_current_mouse_dpi"]()

        self.assertEqual(dpi, 1600)


if __name__ == "__main__":
    unittest.main()
