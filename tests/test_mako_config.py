"""Check how the deployed Mako configuration resolves for real notifications.

The resolver mirrors Mako's criteria semantics for the subset this
configuration uses: the global section applies first, then every matching
``[criteria]`` section in file order, the last value winning. Any other
criteria key makes the test fail instead of being silently misjudged.
"""

import configparser
import re
import unittest
from pathlib import Path

HOME = Path(__file__).parents[1] / "ansible/roles/dotfiles/files/home"
MAKO_CONFIG = HOME / ".config/mako/config"
HYPR_CONFIG = HOME / ".config/hypr/config.lua"
HYPR_KEYBINDINGS = HOME / ".config/hypr/conf/keybindings.lua"
HYPRTOOLKIT_CONFIG = HOME / ".config/hypr/hyprtoolkit.conf"
GTK3_SETTINGS = HOME / ".config/gtk-3.0/settings.ini"
SYSTEM_ICON_ROOT = "/usr/share/icons"
URGENCIES = ("low", "normal", "critical")
SUPPORTED_CRITERIA = {"mode", "urgency"}
DEFAULT_MODE = "default"


def parse_sections(text):
    """Return ``[(criteria, options)]`` with the global section first."""
    sections = [({}, {})]
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            criteria = dict(item.split("=", 1) for item in line[1:-1].split())
            unsupported = set(criteria) - SUPPORTED_CRITERIA
            if unsupported:
                raise ValueError(f"unsupported Mako criteria: {sorted(unsupported)}")
            sections.append((criteria, {}))
            continue
        key, value = line.split("=", 1)
        sections[-1][1][key] = value
    return sections


def resolve(sections, mode, urgency):
    """Return the options Mako applies to a notification in one active mode."""
    style = {}
    for criteria, options in sections:
        if criteria.get("mode", mode) != mode:
            continue
        if criteria.get("urgency", urgency) != urgency:
            continue
        style.update(options)
    return style


class MakoConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sections = parse_sections(MAKO_CONFIG.read_text(encoding="utf-8"))
        cls.global_options = cls.sections[0][1]
        cls.modes = {DEFAULT_MODE} | {
            criteria["mode"] for criteria, _ in cls.sections if "mode" in criteria
        }

    def test_ascending_time_sort_never_truncates_the_newest_notifications(self):
        # Mako keeps the first max-visible entries of its sorted list; with an
        # ascending time sort those are the oldest ones.
        if self.global_options.get("sort", "-time").startswith("+time"):
            self.assertEqual(self.global_options.get("max-visible"), "-1")

    def test_critical_notifications_stay_visible_in_every_mode(self):
        for mode in sorted(self.modes):
            with self.subTest(mode=mode):
                style = resolve(self.sections, mode, "critical")
                self.assertEqual(style.get("invisible", "0"), "0")

    def test_critical_notifications_wait_for_dismissal(self):
        style = resolve(self.sections, DEFAULT_MODE, "critical")
        self.assertEqual(style.get("default-timeout"), "0")
        self.assertNotEqual(
            style.get("border-color"), self.global_options.get("border-color")
        )

    def test_do_not_disturb_still_hides_regular_notifications(self):
        self.assertIn("dnd", self.modes)
        for urgency in ("low", "normal"):
            with self.subTest(urgency=urgency):
                style = resolve(self.sections, "dnd", urgency)
                self.assertEqual(style.get("invisible"), "1")

    def test_default_mode_shows_every_urgency(self):
        for urgency in URGENCIES:
            with self.subTest(urgency=urgency):
                style = resolve(self.sections, DEFAULT_MODE, urgency)
                self.assertEqual(style.get("invisible", "0"), "0")

    def test_critical_notifications_are_drawn_above_fullscreen_windows(self):
        # Hyprland draws fullscreen windows over the "top" layer, which would
        # hide critical alerts during games even when DnD lets them through.
        for mode in sorted(self.modes):
            with self.subTest(mode=mode):
                style = resolve(self.sections, mode, "critical")
                self.assertEqual(style.get("layer"), "overlay")

    def test_notifications_without_timeout_can_be_dismissed_from_the_keyboard(self):
        never_expire = any(
            options.get("default-timeout") == "0" for _, options in self.sections
        )
        if not never_expire:
            self.skipTest("every notification expires on its own")
        dismiss_utils = re.findall(
            r'^\s*(\w+)\s*=\s*"makoctl dismiss"',
            HYPR_CONFIG.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        self.assertTrue(dismiss_utils, "config.lua defines no makoctl dismiss")
        keybindings = HYPR_KEYBINDINGS.read_text(encoding="utf-8")
        self.assertTrue(
            any(f"config.utils.{name}" in keybindings for name in dismiss_utils)
        )

    def test_icons_are_searched_in_the_gtk_icon_theme(self):
        # Mako only searches hicolor and pixmaps unless icon-path lists more.
        gtk = configparser.ConfigParser()
        gtk.read_string(GTK3_SETTINGS.read_text(encoding="utf-8"))
        theme = gtk["Settings"]["gtk-icon-theme-name"]
        icon_paths = self.global_options.get("icon-path", "").split(":")
        self.assertIn(f"{SYSTEM_ICON_ROOT}/{theme}", icon_paths)

    def integer_setting(self, path, name):
        match = re.search(
            rf"^\s*{name}\s*=\s*(\d+)",
            path.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        if match is None:
            self.fail(f"{name} not found in {path.name}")
        return match.group(1)

    def test_geometry_matches_hyprland(self):
        self.assertEqual(
            self.global_options.get("border-radius"),
            self.integer_setting(HYPRTOOLKIT_CONFIG, "rounding_large"),
        )
        gaps = {
            name: self.integer_setting(HYPR_CONFIG, name)
            for name in ("gaps_in", "gaps_out")
        }
        self.assertEqual(gaps["gaps_in"], gaps["gaps_out"])
        self.assertEqual(self.global_options.get("margin"), gaps["gaps_out"])

    def test_resolver_rejects_criteria_it_cannot_evaluate(self):
        with self.assertRaises(ValueError):
            parse_sections("[app-name=firefox]\ninvisible=1\n")


if __name__ == "__main__":
    unittest.main()
