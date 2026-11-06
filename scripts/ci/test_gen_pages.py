import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_PATH = Path(__file__).with_name("gen_pages.py")
REPO_ROOT = SCRIPT_PATH.resolve().parents[2]
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


GITLAB_ENV = {
    "CI_PROJECT_URL": "https://gitlab.example/group/dotfiles",
    "CI_COMMIT_SHA": "0123abc",
}


def broken_relative_links(public):
    """Return (page, url) for every relative href/src missing under public."""
    broken = []
    for page in public.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        for url in re.findall(r'(?:href|src)="([^"]*)"', html):
            path = url.split("#", 1)[0]
            if not path or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:|^//", path):
                continue
            target = Path(os.path.normpath(page.parent / path))
            # A page directory serves its index.html; outside public/, the
            # local preview may link a repository directory directly.
            if target.is_dir() and (target / "index.html").exists():
                target = target / "index.html"
            if not target.exists():
                broken.append((str(page.relative_to(public)), url))
    return broken


class PageOutputPathTests(unittest.TestCase):
    def test_home_is_the_site_index(self):
        self.assertEqual(GEN_PAGES.page_output_path("README.md"), "index.html")

    def test_nested_page_mirrors_its_source_path(self):
        self.assertEqual(
            GEN_PAGES.page_output_path("dist/arch/install.md"),
            "dist/arch/install.md/index.html",
        )

    def test_github_directory_is_published_without_its_dot(self):
        self.assertEqual(
            GEN_PAGES.page_output_path(".github/workflows/README.md"),
            "github/workflows/README.md/index.html",
        )


class RewriteUrlTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for name in ("README.md", "docs/a.md", "docs/b.md", ".github/x.md"):
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            (self.root / name).write_text("# t\n", encoding="utf-8")
        (self.root / "docs/shot.webp").write_bytes(b"img")
        (self.root / ".github/flow.png").write_bytes(b"img")
        (self.root / "scripts").mkdir()
        (self.root / "scripts/run.sh").write_text("", encoding="utf-8")
        self.sources = ["README.md", "docs/a.md", "docs/b.md", ".github/x.md"]

    def site(self, repo_url=None):
        return GEN_PAGES.Site(
            str(self.root), str(self.root / "public"), self.sources, repo_url
        )

    def rewrite(self, site, url, source="docs/a.md"):
        return site.rewrite_url(url, source, GEN_PAGES.page_output_path(source))

    def test_sibling_markdown_link_targets_its_page(self):
        self.assertEqual(
            self.rewrite(self.site(), "./b.md#part"), "../b.md/index.html#part"
        )

    def test_link_to_github_page_uses_published_path(self):
        self.assertEqual(
            self.rewrite(self.site(), "./.github/x.md", source="README.md"),
            "github/x.md/index.html",
        )

    def test_image_is_copied_and_linked_relatively(self):
        site = self.site()

        self.assertEqual(self.rewrite(site, "shot.webp"), "../shot.webp")
        self.assertEqual(site.assets, {"docs/shot.webp"})

    def test_repository_file_and_directory_use_repository_browser(self):
        template = GEN_PAGES.repository_url_template(GITLAB_ENV)
        site = self.site(template)

        self.assertEqual(
            self.rewrite(site, "../scripts/run.sh"),
            "https://gitlab.example/group/dotfiles/-/blob/0123abc/scripts/run.sh",
        )
        self.assertEqual(
            self.rewrite(site, "../scripts/"),
            "https://gitlab.example/group/dotfiles/-/tree/0123abc/scripts",
        )

    def test_repository_file_without_ci_points_to_the_checkout(self):
        self.assertEqual(
            self.rewrite(self.site(), "../scripts/run.sh"),
            "../../../scripts/run.sh",
        )

    def test_external_and_anchor_links_are_untouched(self):
        site = self.site()

        for url in ("https://example.org/a.md", "#local", "mailto:a@b.c", "/abs"):
            self.assertEqual(self.rewrite(site, url), url)

    def test_missing_target_is_reported_and_kept(self):
        site = self.site()

        self.assertEqual(self.rewrite(site, "nope.md"), "nope.md")
        self.assertEqual(site.missing_links, [("docs/a.md", "nope.md")])

    def test_github_actions_repository_template(self):
        template = GEN_PAGES.repository_url_template(
            {
                "GITHUB_SERVER_URL": "https://github.com",
                "GITHUB_REPOSITORY": "o/r",
                "GITHUB_SHA": "f00",
            }
        )

        self.assertEqual(template, "https://github.com/o/r/{kind}/f00/{path}")


class RewriteLinksTests(unittest.TestCase):
    """Links found in rendered HTML, as render_page passes them."""

    # Same fixture as RewriteUrlTests, without inheriting (and rerunning) its tests.
    setUp = RewriteUrlTests.setUp
    site = RewriteUrlTests.site
    rewrite = RewriteUrlTests.rewrite

    def links(self, markdown_text, source="docs/a.md"):
        return self.site().rewrite_links(
            GEN_PAGES.render_markdown(markdown_text),
            source,
            GEN_PAGES.page_output_path(source),
        )

    def test_code_span_showing_a_tag_is_left_alone(self):
        html = self.links('Write `<img src="b.md">` in a page.')

        self.assertIn('src="b.md"', html)
        self.assertNotIn("index.html", html)

    def test_single_quoted_raw_html_attribute_is_rewritten(self):
        html = self.links("<img src='shot.webp' alt='x'>")

        self.assertIn('src="../shot.webp"', html)

    def test_query_and_fragment_are_kept(self):
        self.assertEqual(
            self.rewrite(self.site(), "b.md?plain=1#part"),
            "../b.md/index.html?plain=1#part",
        )

    def test_image_under_github_is_published_under_github(self):
        site = self.site()

        self.assertEqual(
            self.rewrite(site, "flow.png", source=".github/x.md"), "../flow.png"
        )
        self.assertEqual(site.assets, {".github/flow.png"})
        self.assertEqual(
            GEN_PAGES.published_path(".github/flow.png"), "github/flow.png"
        )


class PageTitleTests(unittest.TestCase):
    def test_heading_comes_from_rendered_html_not_code_blocks(self):
        html = GEN_PAGES.render_markdown(
            "Intro\n\n    # install deps\n\n## The `foo` [plugin](x.md)\n"
        )

        self.assertEqual(GEN_PAGES.page_title("p.md", html), "The foo plugin")

    def test_page_without_heading_uses_its_path(self):
        self.assertEqual(GEN_PAGES.page_title("p.md", "<p>text</p>"), "p.md")


class DiscoverMarkdownTests(unittest.TestCase):
    def test_walk_without_git_skips_submodules_and_build_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in (
                "README.md",
                "docs/a.md",
                "vendor/lib/README.md",
                "public/x.md",
            ):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_text("# t\n", encoding="utf-8")
            (root / ".gitmodules").write_text(
                '[submodule "lib"]\n\tpath = vendor/lib\n', encoding="utf-8"
            )

            # tmp is not a Git work tree, so discovery falls back to the walk.
            self.assertEqual(
                GEN_PAGES.discover_markdown(str(root)), ["README.md", "docs/a.md"]
            )

    def test_inherited_git_dir_does_not_replace_the_root_repository(self):
        # Git hooks run from a linked worktree get GIT_DIR; `git -C root` must
        # still describe root, not the repository the hook runs for.
        with tempfile.TemporaryDirectory() as tmp:
            other, root = Path(tmp) / "other", Path(tmp) / "root"
            other.mkdir()
            root.mkdir()
            subprocess.run(
                ["git", "init", "-q", str(other)],
                check=True,
                env=GEN_PAGES.env_for_root_repository(),
            )
            (root / "README.md").write_text("# t\n", encoding="utf-8")

            with mock.patch.dict(os.environ, {"GIT_DIR": str(other / ".git")}):
                self.assertEqual(GEN_PAGES.discover_markdown(str(root)), ["README.md"])


class SmallSiteTests(unittest.TestCase):
    """build_site and the command line on a throwaway repository."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "repo"
        self.root.mkdir()
        self.write("README.md", "# Home\n\n[a](docs/a.md)\n")
        self.write("docs/a.md", "# A\n")
        self.public = Path(tmp.name) / "public"

    def write(self, name, text):
        (self.root / name).parent.mkdir(parents=True, exist_ok=True)
        (self.root / name).write_text(text, encoding="utf-8")

    def test_page_of_a_removed_source_is_deleted(self):
        GEN_PAGES.build_site(str(self.root), str(self.public), {})
        (self.root / "docs/a.md").unlink()
        self.write("README.md", "# Home\n")

        GEN_PAGES.build_site(str(self.root), str(self.public), {})

        self.assertFalse((self.public / "docs").exists())
        self.assertTrue((self.public / "index.html").is_file())

    def test_directory_not_made_by_a_build_is_not_pruned(self):
        self.public.mkdir()
        (self.public / "keep.txt").write_text("mine", encoding="utf-8")

        GEN_PAGES.build_site(str(self.root), str(self.public), {})

        self.assertTrue((self.public / "keep.txt").is_file())

    def test_output_directory_containing_the_sources_is_refused(self):
        with self.assertRaises(ValueError):
            GEN_PAGES.build_site(str(self.root), str(self.root.parent), {})
        self.assertTrue((self.root / "docs/a.md").is_file())

    def test_command_fails_on_a_broken_link(self):
        self.write("docs/a.md", "# A\n\n[gone](missing.md)\n")

        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), str(self.root), str(self.public)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("docs/a.md: link target not found: missing.md", result.stderr)


class BuildSiteTests(unittest.TestCase):
    """Build the real repository documentation, as the Pages jobs do."""

    def build(self, env):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        public = Path(tmp.name) / "public"
        site = GEN_PAGES.build_site(str(REPO_ROOT), str(public), env)
        return site, public

    def test_every_markdown_file_is_published(self):
        site, public = self.build(GITLAB_ENV)

        for source in GEN_PAGES.discover_markdown(str(REPO_ROOT)):
            with self.subTest(source=source):
                self.assertTrue((public / site.pages[source]).is_file())

    def test_published_site_has_no_broken_relative_link(self):
        for env in (GITLAB_ENV, {}):
            with self.subTest(ci=bool(env)):
                site, public = self.build(env)

                self.assertEqual(site.missing_links, [])
                self.assertEqual(broken_relative_links(public), [])


if __name__ == "__main__":
    unittest.main()
