"""Check the deployed Mako configuration against the behavior it promises.

The resolver mirrors Mako's criteria matching for ``mode`` and ``urgency``
only, with one active mode at a time: the global section applies first, then
every matching ``[criteria]`` section in file order, the last value winning.
Any other criteria key makes the test fail instead of being misjudged.

The resolver also matches ``grouped`` criteria, but does not model how Mako
forms groups, its surfaces, or the timeout a sender requests. Dedicated tests
check the options Mako reads for those instead.

Testing each mode alone also covers several active modes (``makoctl mode -a``):
the last matching section belongs to a single mode, and it applies the same
way when that mode is active alone.
"""

import configparser
import json
import re
import unittest
from pathlib import Path

import jinja2
import yaml

HOME = Path(__file__).parents[1] / "ansible/roles/dotfiles/files/home"
TEMPLATES = Path(__file__).parents[1] / "ansible/roles/dotfiles/templates/home"
DOTFILES_DEFAULTS = (
    Path(__file__).parents[1] / "ansible/roles/dotfiles/defaults/main.yml"
)
HYPR_CONFIG = HOME / ".config/hypr/config.lua"
HYPR_KEYBINDINGS = HOME / ".config/hypr/conf/keybindings.lua"
WAYBAR_STYLE = HOME / ".config/waybar/style.css"
# Captures the RGB part of #rrggbb and #rrggbbaa colors.
HEX_COLOR = re.compile(r"#([0-9a-fA-F]{6})([0-9a-fA-F]{2})?\b")
HYPR_WINDOW_RULES = HOME / ".config/hypr/conf/windowrules.lua"
SYSTEM_ICON_ROOT = "/usr/share/icons"
URGENCIES = ("low", "normal", "critical")
SUPPORTED_CRITERIA = {"mode", "urgency", "grouped"}
TRUE_VALUES = {"1", "true"}
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


def resolve(sections, mode, urgency, grouped=False):
    """Return the options Mako applies to a notification in one active mode."""
    style = {}
    for criteria, options in sections:
        if "grouped" in criteria and (criteria["grouped"] in TRUE_VALUES) != grouped:
            continue
        if criteria.get("mode", mode) != mode:
            continue
        if criteria.get("urgency", urgency) != urgency:
            continue
        style.update(options)
    return style


class MakoConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.defaults = yaml.safe_load(DOTFILES_DEFAULTS.read_text(encoding="utf-8"))
        cls.template_environment = jinja2.Environment(
            loader=jinja2.FileSystemLoader(TEMPLATES)
        )
        cls.rendered = cls.render_configs(cls.defaults["dotfiles_icon_theme"])
        cls.sections = parse_sections(cls.rendered["mako"])
        cls.global_options = cls.sections[0][1]
        cls.modes = {DEFAULT_MODE} | {
            criteria["mode"] for criteria, _ in cls.sections if "mode" in criteria
        }

    @classmethod
    def render_configs(cls, icon_theme):
        context = {
            "dotfiles_icon_theme": icon_theme,
            "dotfiles_icon_theme_parent": icon_theme.replace("-Dark", ""),
        }
        templates = {
            "gtk2": ".gtkrc-2.0.j2",
            "gtk3": ".config/gtk-3.0/settings.ini.j2",
            "hyprtoolkit": ".config/hypr/hyprtoolkit.conf.j2",
            "mako": ".config/mako/config.j2",
        }
        return {
            name: cls.template_environment.get_template(template).render(**context)
            for name, template in templates.items()
        }

    def test_newest_notification_sits_in_the_anchor_corner(self):
        # Mako draws its sorted list from the top of the surface down.
        anchor = self.global_options.get("anchor", "top-right")
        sort = self.global_options.get("sort", "-time")
        expected = "+time" if anchor.startswith("bottom") else "-time"
        self.assertTrue(sort.startswith(expected), (anchor, sort))

    def test_stack_limit_only_hides_the_oldest_notifications(self):
        # Mako keeps the first max-visible entries of its sorted list; with an
        # ascending time sort those are the oldest, so a limit would hide the
        # newest notifications instead.
        max_visible = int(self.global_options.get("max-visible", "5"))
        if self.global_options.get("sort", "-time").startswith("+time"):
            self.assertEqual(max_visible, -1)
        else:
            self.assertGreater(max_visible, 0, "a burst could cover the screen")

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
        # Mako needs both Papirus-Dark and its Papirus parent explicitly.
        gtk3 = configparser.ConfigParser()
        gtk3.read_string(self.rendered["gtk3"])
        gtk2 = re.search(
            r'^gtk-icon-theme-name="([^"]+)"',
            self.rendered["gtk2"],
            re.MULTILINE,
        )
        toolkit = re.search(
            r"^icon_theme\s*=\s*(\S+)",
            self.rendered["hyprtoolkit"],
            re.MULTILINE,
        )
        if gtk2 is None or toolkit is None:
            self.fail("icon theme not found in a rendered GTK or hyprtoolkit config")
        themes = {
            "gtk-3.0/settings.ini": gtk3["Settings"]["gtk-icon-theme-name"],
            ".gtkrc-2.0": gtk2.group(1),
            "hyprtoolkit.conf": toolkit.group(1),
            "mako": self.global_options["icon-path"].split(":")[0].rsplit("/", 1)[-1],
        }
        self.assertEqual(len(set(themes.values())), 1, themes)
        icon_paths = self.global_options.get("icon-path", "").split(":")
        self.assertEqual(
            icon_paths,
            [
                f"{SYSTEM_ICON_ROOT}/{themes['.gtkrc-2.0']}",
                f"{SYSTEM_ICON_ROOT}/Papirus",
            ],
        )

    def test_icon_theme_variable_renders_every_configuration(self):
        rendered = self.render_configs("Example-Dark")
        self.assertIn('gtk-icon-theme-name="Example-Dark"', rendered["gtk2"])
        gtk3 = configparser.ConfigParser()
        gtk3.read_string(rendered["gtk3"])
        self.assertEqual(gtk3["Settings"]["gtk-icon-theme-name"], "Example-Dark")
        self.assertIsNotNone(
            re.search(r"^icon_theme = Example-Dark$", rendered["hyprtoolkit"], re.M)
        )
        mako = parse_sections(rendered["mako"])[0][1]
        self.assertEqual(
            mako["icon-path"],
            f"{SYSTEM_ICON_ROOT}/Example-Dark:{SYSTEM_ICON_ROOT}/Example",
        )
        nwg_look = json.loads((HOME / ".config/nwg-look/config").read_text())
        self.assertFalse(nwg_look["export-gtkrc-20"])

    def test_colors_come_from_the_shared_gruvbox_palette(self):
        palette = {
            rgb.lower()
            for rgb, _ in HEX_COLOR.findall(WAYBAR_STYLE.read_text(encoding="utf-8"))
        }
        colors = [
            (criteria, key, rgb)
            for criteria, options in self.sections
            for key, value in options.items()
            for rgb, _ in HEX_COLOR.findall(value)
        ]
        self.assertTrue(colors)
        for criteria, key, rgb in colors:
            with self.subTest(criteria=criteria, option=key):
                self.assertIn(rgb.lower(), palette)

    def test_translucent_background_is_blurred_by_hyprland(self):
        match = HEX_COLOR.fullmatch(self.global_options.get("background-color", ""))
        self.assertIsNotNone(match, "background-color is not #rrggbb[aa]")
        alpha = match.group(2) if match else None
        if alpha is None or alpha.lower() == "ff":
            self.skipTest("the background is opaque")
        rules = HYPR_WINDOW_RULES.read_text(encoding="utf-8")
        self.assertRegex(
            rules,
            r'hl\.layer_rule\(\{\s*match\s*=\s*\{\s*namespace\s*=\s*"notifications"'
            r"\s*\},[^)]*blur\s*=\s*true",
        )

    def test_every_notification_shows_its_application(self):
        for grouped in (False, True):
            with self.subTest(grouped=grouped):
                style = resolve(self.sections, DEFAULT_MODE, "normal", grouped)
                self.assertIn("%a", style.get("format", ""))
        grouped_style = resolve(self.sections, DEFAULT_MODE, "normal", True)
        self.assertIn("%g", grouped_style.get("format", ""))

    def test_low_urgency_is_styled_apart(self):
        borders = {
            urgency: resolve(self.sections, DEFAULT_MODE, urgency).get("border-color")
            for urgency in URGENCIES
        }
        self.assertEqual(len(set(borders.values())), len(URGENCIES), borders)

    def integer_setting(self, path, name):
        content = path.read_text(encoding="utf-8") if isinstance(path, Path) else path
        match = re.search(
            rf"^\s*{name}\s*=\s*(\d+)",
            content,
            re.MULTILINE,
        )
        if match is None:
            self.fail(f"{name} not found in {path.name}")
        return match.group(1)

    def test_geometry_matches_hyprland(self):
        self.assertEqual(
            self.global_options.get("border-radius"),
            self.integer_setting(self.rendered["hyprtoolkit"], "rounding_large"),
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
