import json
import shlex
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

INSTALL_SCRIPT = Path(__file__).parents[1] / "install"


class InstallPackageStateTests(unittest.TestCase):
    def run_bash(self, body):
        script = f"source {shlex.quote(str(INSTALL_SCRIPT))}\n{body}"
        return subprocess.run(
            ["bash", "-c", script],
            check=True,
            capture_output=True,
            text=True,
        )

    def test_state_round_trip_is_atomic_and_private(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            state_path = Path(temporary_directory) / "state" / "packages.json"
            result = self.run_bash(f"""
PACKAGE_STATE_FILE={shlex.quote(str(state_path))}
groups=(11_hyprland 01_base)
packages=(vulkan-radeon auto-cpufreq)
write_package_state groups packages
load_package_state
printf 'loaded=%s\n' "$PACKAGE_STATE_LOADED"
printf 'groups=%s\n' "${{PREVIOUS_SELECTED_GROUPS[*]}}"
printf 'packages=%s\n' "${{PREVIOUS_OWNED_PACKAGES[*]}}"
""")

            state = json.loads(state_path.read_text(encoding="utf-8"))
            state_mode = stat.S_IMODE(state_path.stat().st_mode)

        self.assertIn("loaded=true", result.stdout)
        self.assertEqual(state["selected_groups"], ["01_base", "11_hyprland"])
        self.assertEqual(state["owned_packages"], ["auto-cpufreq", "vulkan-radeon"])
        self.assertEqual(state_mode, 0o600)

    def test_invalid_state_disables_removal(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            state_path = Path(temporary_directory) / "packages.json"
            state_path.write_text('{"version": 999}\n', encoding="utf-8")
            result = self.run_bash(f"""
PACKAGE_STATE_FILE={shlex.quote(str(state_path))}
load_package_state
printf 'loaded=%s groups=%d packages=%d\n' \
    "$PACKAGE_STATE_LOADED" \
    "${{#PREVIOUS_SELECTED_GROUPS[@]}}" \
    "${{#PREVIOUS_OWNED_PACKAGES[@]}}"
""")

        self.assertIn("loaded=false groups=0 packages=0", result.stdout)
        self.assertIn("automatic removal is disabled", result.stdout)

    def test_package_action_is_not_forwarded_to_dotbot(self):
        result = self.run_bash("""
parse_install_args --reconcile-packages --force-color
printf 'action=%s args=%s\n' "$PACKAGE_ACTION" "${DOTBOT_ARGS[*]}"
""")

        self.assertEqual(result.stdout, "action=reconcile args=--force-color\n")

    def test_help_exits_without_starting_installation(self):
        result = subprocess.run(
            [INSTALL_SCRIPT, "--help"],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("Usage: ./install [OPTIONS]", result.stdout)
        self.assertIn("--package-plan", result.stdout)
        self.assertIn("--reconcile-packages", result.stdout)
        self.assertNotIn("Starting dotfiles installation", result.stdout)

    def test_critical_packages_are_protected(self):
        result = self.run_bash("""
for package in base linux-cachyos pacman sudo; do
    is_protected_package "$package"
done
if is_protected_package firefox; then
    exit 1
fi
""")

        self.assertEqual(result.returncode, 0)

    def test_removal_candidates_require_ownership_and_exclude_desired(self):
        result = self.run_bash("""
declare -A installed=(
    [managed-stale]=1
    [managed-current]=1
    [user-package]=1
    [linux-cachyos]=1
)
declare -A desired=([managed-current]=1)
declare -A owned=(
    [managed-stale]=1
    [managed-current]=1
    [linux-cachyos]=1
)
candidates=()
collect_removal_candidates installed desired owned candidates
printf '%s\n' "${candidates[@]}"
""")

        self.assertEqual(result.stdout.splitlines()[-1], "managed-stale")

    def test_graphics_detection_selects_each_vendor(self):
        cases = {
            "amd": (
                "AMD/ATI Navi 22 [1002:73df]",
                ["08_amd"],
            ),
            "intel": (
                "Intel TigerLake-LP GT2 [Iris Xe Graphics] [8086:9a49]",
                ["08_intel_modern"],
            ),
            "nvidia": (
                "NVIDIA AD107 [GeForce RTX 4060] [10de:2882]",
                ["09_nvidia_modern"],
            ),
            "intel_nvidia_hybrid": (
                "Intel UHD Graphics 630 [8086:3e9b]\n"
                "0000:01:00.0 3D controller [0302]: "
                "NVIDIA TU117M [GeForce GTX 1650 Mobile] [10de:1f91]",
                ["08_intel_modern", "09_nvidia_modern"],
            ),
        }

        for name, (controllers, expected) in cases.items():
            with self.subTest(name=name):
                pci_devices = (
                    "0000:00:02.0 VGA compatible controller [0300]: " + controllers
                )
                result = self.run_bash(
                    "detect_graphics_package_groups_from_pci "
                    f"{shlex.quote(pci_devices)}"
                )
                self.assertEqual(result.stdout.splitlines(), expected)

    def test_standard_package_groups_are_selected_by_default(self):
        result = self.run_bash(r"""
PACKAGE_GROUP_DEFAULTS=()
apply_standard_package_defaults
printf '%s\n' "${!PACKAGE_GROUP_DEFAULTS[@]}" | sort
""")

        self.assertEqual(
            result.stdout.splitlines(), ["01_base", "03_gtk", "11_hyprland"]
        )

    def test_graphics_detection_selects_legacy_generations(self):
        result = self.run_bash(r"""
pci_devices='0000:00:02.0 VGA compatible controller [0300]: Intel Corporation 4th Gen Core Processor Integrated Graphics Controller [8086:0412]
0000:01:00.0 3D controller [0302]: NVIDIA Corporation GP107M [GeForce GTX 1050 Mobile] [10de:1c8d]'
detect_graphics_package_groups_from_pci "$pci_devices"
""")

        self.assertEqual(
            result.stdout.splitlines(),
            ["07_intel_legacy", "09_nvidia_legacy"],
        )

    def test_hybrid_graphics_replaces_stale_gpu_defaults_only(self):
        result = self.run_bash(r"""
PACKAGE_GROUP_DEFAULTS=([01_base]=1 [08_amd]=1 [09_nvidia_legacy]=1)
detect_graphics_package_groups() {
    printf '%s\n' 08_intel_modern 09_nvidia_modern
}
apply_detected_graphics_defaults
printf '%s\n' "${!PACKAGE_GROUP_DEFAULTS[@]}" | sort
""")

        self.assertEqual(
            result.stdout.splitlines()[-3:],
            ["01_base", "08_intel_modern", "09_nvidia_modern"],
        )

    def test_unneeded_graphics_packages_exclude_selected_and_shared_packages(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            package_directory = Path(temporary_directory)
            amd_file = package_directory / "08_amd.txt"
            intel_file = package_directory / "08_intel_modern.txt"
            nvidia_legacy_file = package_directory / "09_nvidia_legacy.txt"
            nvidia_modern_file = package_directory / "09_nvidia_modern.txt"
            amd_file.write_text("vulkan-radeon\n", encoding="utf-8")
            intel_file.write_text("vulkan-intel\n", encoding="utf-8")
            nvidia_legacy_file.write_text(
                "libva-nvidia-driver\nnvidia-580xx-utils\n", encoding="utf-8"
            )
            nvidia_modern_file.write_text(
                "libva-nvidia-driver\nnvidia-utils\n", encoding="utf-8"
            )
            files = " ".join(
                shlex.quote(str(path))
                for path in (
                    amd_file,
                    intel_file,
                    nvidia_legacy_file,
                    nvidia_modern_file,
                )
            )
            result = self.run_bash(f"""
files=({files})
selected_groups=(08_intel_modern 09_nvidia_modern)
declare -A installed=(
    [vulkan-radeon]=1
    [vulkan-intel]=1
    [libva-nvidia-driver]=1
    [nvidia-580xx-utils]=1
    [nvidia-utils]=1
)
declare -A desired=(
    [vulkan-intel]=1
    [libva-nvidia-driver]=1
    [nvidia-utils]=1
)
candidates=()
collect_unneeded_graphics_packages \
    files selected_groups installed desired candidates
printf '%s\n' "${{candidates[@]}}"
""")

        self.assertEqual(
            result.stdout.splitlines(), ["nvidia-580xx-utils", "vulkan-radeon"]
        )


if __name__ == "__main__":
    unittest.main()
