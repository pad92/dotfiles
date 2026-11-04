"""Check the deployed Mako configuration against the behavior it promises.

The resolver mirrors Mako's criteria matching for ``mode`` and ``urgency``
only, with one active mode at a time: the global section applies first, then
every matching ``[criteria]`` section in file order, the last value winning.
Any other criteria key makes the test fail instead of being misjudged.

The resolver does not model surfaces, grouping, or the timeout a sender
requests. Dedicated tests check the options Mako reads for those instead.

Testing each mode alone also covers several active modes (``makoctl mode -a``):
the last matching section belongs to a single mode, and it applies the same
way when that mode is active alone.
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
GTK2_SETTINGS = HOME / ".gtkrc-2.0"
WAYBAR_STYLE = HOME / ".config/waybar/style.css"
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}\b")
SYSTEM_ICON_ROOT = "/usr/share/icons"
URGENCIES = ("low", "normal", "critical")
SUPPORTED_CRITERIA = {"mode", "urgency"}
# Mako draws one surface per (output, layer, anchor); see criteria.c in 1.11.
SURFACE_OPTIONS = ("output", "layer", "anchor")
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
        # default-timeout only applies when the sender requests no timeout.
        self.assertEqual(style.get("ignore-timeout"), "1")
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

    def test_every_notification_shares_one_stack(self):
        # A criteria section that changes a surface option opens a second
        # surface at the same corner, and the two stacks draw over each other.
        for criteria, options in self.sections[1:]:
            with self.subTest(criteria=criteria):
                self.assertFalse(set(SURFACE_OPTIONS) & set(options))

    def test_grouping_never_mixes_urgencies(self):
        group_by = self.global_options.get("group-by")
        if group_by is None:
            self.skipTest("notifications are not grouped")
        self.assertIn("urgency", group_by.split(","))

    def test_notifications_without_timeout_are_all_dismissed_from_the_keyboard(self):
        # Without an id, makoctl dismiss closes the first listed notification:
        # with sort=+time the oldest, possibly one hidden by do-not-disturb.
        never_expire = any(
            options.get("default-timeout") == "0" for _, options in self.sections
        )
        if not never_expire:
            self.skipTest("every notification expires on its own")
        dismiss_utils = re.findall(
            r'^\s*(\w+)\s*=\s*"makoctl dismiss (?:--all|-a)"',
            HYPR_CONFIG.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        self.assertTrue(dismiss_utils, "config.lua defines no makoctl dismiss --all")
        keybindings = HYPR_KEYBINDINGS.read_text(encoding="utf-8")
        self.assertTrue(
            any(f"config.utils.{name}" in keybindings for name in dismiss_utils)
        )

    def test_icon_theme_is_declared_consistently(self):
        # The theme name is written by hand in four files; Mako only searches
        # hicolor and pixmaps unless icon-path lists the theme first.
        gtk3 = configparser.ConfigParser()
        gtk3.read_string(GTK3_SETTINGS.read_text(encoding="utf-8"))
        gtk2 = re.search(
            r'^gtk-icon-theme-name="([^"]+)"',
            GTK2_SETTINGS.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        toolkit = re.search(
            r"^icon_theme\s*=\s*(\S+)",
            HYPRTOOLKIT_CONFIG.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        if gtk2 is None or toolkit is None:
            self.fail("icon theme not found in .gtkrc-2.0 or hyprtoolkit.conf")
        themes = {
            "gtk-3.0/settings.ini": gtk3["Settings"]["gtk-icon-theme-name"],
            ".gtkrc-2.0": gtk2.group(1),
            "hyprtoolkit.conf": toolkit.group(1),
        }
        self.assertEqual(len(set(themes.values())), 1, themes)
        icon_paths = self.global_options.get("icon-path", "").split(":")
        self.assertEqual(icon_paths[0], f"{SYSTEM_ICON_ROOT}/{themes['.gtkrc-2.0']}")

    def test_colors_come_from_the_shared_gruvbox_palette(self):
        palette = {
            color.lower()
            for color in HEX_COLOR.findall(WAYBAR_STYLE.read_text(encoding="utf-8"))
        }
        for criteria, options in self.sections:
            for key, value in options.items():
                for color in HEX_COLOR.findall(value):
                    with self.subTest(criteria=criteria, option=key):
                        self.assertIn(color.lower(), palette)

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
