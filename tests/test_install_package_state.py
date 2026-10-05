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


if __name__ == "__main__":
    unittest.main()
