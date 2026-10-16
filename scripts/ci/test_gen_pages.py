import importlib.util
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).with_name("gen_pages.py")
SPEC = importlib.util.spec_from_file_location("gen_pages", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load {SCRIPT_PATH}")
GEN_PAGES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GEN_PAGES)


class RenderMarkdownTests(unittest.TestCase):
    def test_nested_unordered_lists_keep_three_levels(self):
        rendered = GEN_PAGES.render_markdown(
            "- parent\n  - child\n    - grandchild\n      continuation"
        )

        self.assertEqual(rendered.count("<ul>"), 3)
        self.assertIn("grandchild\n  continuation", rendered)

    def test_nested_ordered_list_is_preserved(self):
        rendered = GEN_PAGES.render_markdown("1. parent\n   1. child")

        self.assertEqual(rendered.count("<ol>"), 2)

    def test_alert_supports_compact_nested_lists(self):
        rendered = GEN_PAGES.parse_alerts("> [!NOTE]\n> - parent\n>   - child")

        self.assertEqual(rendered.count("<ul>"), 2)

    def test_blockquote_supports_compact_nested_lists(self):
        rendered = GEN_PAGES.render_markdown("> - parent\n>   - child")

        self.assertEqual(rendered.count("<ul>"), 2)

    def test_indented_top_level_list_stays_a_list(self):
        rendered = GEN_PAGES.render_markdown("  - standalone")

        self.assertIn("<ul>", rendered)
        self.assertNotIn("codehilite", rendered)

    def test_indented_thematic_break_stays_a_break(self):
        rendered = GEN_PAGES.render_markdown("  * * *")

        self.assertEqual(rendered, "<hr />")

    def test_indented_code_keeps_its_contents(self):
        rendered = GEN_PAGES.render_markdown("    print('ok')")

        self.assertIn("<code>print('ok')", rendered)
        self.assertNotIn("<code>  print('ok')", rendered)


if __name__ == "__main__":
    unittest.main()
