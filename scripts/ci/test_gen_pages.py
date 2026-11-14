import importlib.util
import os
import posixpath
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

    def test_heading_id_keeps_accents_like_the_forges(self):
        rendered = GEN_PAGES.render_markdown("## Présentation générale")

        self.assertIn('id="présentation-générale"', rendered)


class CodeBlockTests(unittest.TestCase):
    """Fenced code blocks as render_page extracts and reinserts them."""

    def body(self, markdown_text):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "README.md").write_text(markdown_text, encoding="utf-8")
        site = GEN_PAGES.Site(str(root), str(root / "public"), ["README.md"], None)
        return GEN_PAGES.render_page(site, "README.md")

    def test_longer_fence_shows_an_inner_fence_as_code(self):
        html = self.body("````markdown\n```bash\necho hi\n```\n````\n\nafter\n")

        self.assertEqual(html.count('<div class="codehilite">'), 1)
        self.assertIn("```bash", html)
        self.assertIn("<p>after</p>", html)

    def test_tilde_fence_is_a_code_block(self):
        html = self.body("~~~sh\nls\n~~~\n")

        self.assertIn('<div class="codehilite">', html)
        self.assertNotIn("~~~", html)

    def test_info_string_after_the_language_keeps_a_block(self):
        html = self.body('```python title="a.py"\nx = 1\n```\n')

        self.assertIn("<pre>", html)
        self.assertNotIn("title=", html)

    def test_code_block_inside_an_alert_is_highlighted(self):
        html = self.body("> [!NOTE]\n> ```sh\n> ls\n>\n> pwd\n> ```\n\nafter\n")

        self.assertIn('<div class="markdown-alert markdown-alert-note">', html)
        self.assertIn("<pre>", html)
        self.assertNotIn("```", html)
        self.assertIn("<p>after</p>", html)

    def test_toc_marker_in_a_code_span_is_kept(self):
        html = self.body("# T\n\nWrite `[[_TOC_]]` on GitLab.\n")

        self.assertIn("<code>[[_TOC_]]</code>", html)

    def test_toc_marker_on_its_own_line_is_a_toc(self):
        html = self.body("# T\n\n[[_TOC_]]\n\n## Part\n")

        self.assertIn('class="toc"', html)


class ThemeTests(unittest.TestCase):
    """The site's colours follow the Gruvbox palette of the Hyprland desktop."""

    HYPRTOOLKIT = (
        REPO_ROOT
        / "ansible/roles/dotfiles/templates/home/.config/hypr/hyprtoolkit.conf.j2"
    )

    @staticmethod
    def css():
        return SCRIPT_PATH.with_name("style.css").read_text(encoding="utf-8")

    @staticmethod
    def variables(block):
        return dict(re.findall(r"--([\w-]+): (#[0-9a-f]{6});", block))

    def dark_root(self):
        return re.search(r"^:root \{(.*?)^\}", self.css(), re.M | re.S).group(1)

    def light_root(self):
        return re.search(
            r"^:root\[data-theme='light'\] \{(.*?)^\}", self.css(), re.M | re.S
        ).group(1)

    def test_css_colours_match_the_hyprtoolkit_palette(self):
        toolkit = dict(
            re.findall(
                r"^(\w+) = 0x[0-9A-Fa-f]{2}([0-9A-Fa-f]{6})$",
                self.HYPRTOOLKIT.read_text(encoding="utf-8"),
                re.M,
            )
        )
        variables = self.variables(self.dark_root())

        pairs = {
            "bg-color": "background",
            "surface-color": "base",
            "code-inline-bg": "alternate_base",
            "text-color": "text",
            "accent-color": "accent",
            "link-color": "accent",
        }
        for variable, key in pairs.items():
            with self.subTest(variable=variable):
                self.assertEqual(variables[variable], "#" + toolkit[key].lower())

    def test_light_theme_overrides_every_colour_with_gruvbox_light(self):
        dark = self.variables(self.dark_root())
        light = self.variables(self.light_root())

        self.assertEqual(set(light), set(dark))
        self.assertEqual(light["bg-color"], "#fbf1c7")
        self.assertEqual(light["text-color"], "#3c3836")
        self.assertIn("color-scheme: light", self.light_root())

    def test_rules_use_variables_rather_than_literal_colours(self):
        rules = re.sub(r"^\s*--[\w-]+: [^;]+;", "", self.css(), flags=re.M)

        self.assertEqual(re.findall(r"#[0-9a-fA-F]{6}\b|rgba?\(", rules), [])

    def test_css_keeps_no_catppuccin_colour(self):
        css = self.css().lower()

        for colour in ("#cba6f7", "#1e1e2e", "#cdd6f4", "#181825", "#f38ba8"):
            with self.subTest(colour=colour):
                self.assertNotIn(colour, css)

    @unittest.skipUnless(GEN_PAGES._HAVE_PYGMENTS, "requires pygments")
    def test_code_highlighting_uses_gruvbox(self):
        css = GEN_PAGES.pygments_css()

        self.assertIn("#928374", css)  # gruvbox-dark comments
        self.assertNotIn("#ff79c6", css)  # dracula pink
        light = "\n".join(
            line
            for line in css.lower().splitlines()
            if line.startswith(GEN_PAGES.LIGHT_THEME + " .codehilite .")
        )
        self.assertIn("#928374", light)  # gruvbox-light comments
        self.assertIn("#9d0006", light)  # gruvbox-light keywords

    @unittest.skipUnless(GEN_PAGES._HAVE_PYGMENTS, "requires pygments")
    def test_light_theme_resets_tokens_only_the_dark_style_colours(self):
        reset_line = next(
            line
            for line in GEN_PAGES.pygments_css().splitlines()
            if "color:inherit" in line
        )
        reset = reset_line.split("{", 1)[0].split(",")
        light = GEN_PAGES.LIGHT_THEME + " .codehilite "

        # Punctuation and whitespace are #dddddd in gruvbox-dark only.
        self.assertIn(light + ".p", reset)
        self.assertIn(light + ".w", reset)
        self.assertNotIn(light + ".k", reset)

    @unittest.skipUnless(GEN_PAGES._HAVE_PYGMENTS, "requires pygments")
    def test_code_box_background_stays_transparent_in_both_themes(self):
        last = GEN_PAGES.pygments_css().strip().splitlines()[-1]

        self.assertIn(":root[data-theme] .codehilite", last)
        self.assertIn("background:transparent", last)


class FaviconTests(unittest.TestCase):
    """The site icons are published at the root and linked from every page."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "README.md").write_text("# Home\n", encoding="utf-8")
        (root / "docs/a.md").write_text("# A\n", encoding="utf-8")
        self.public = Path(tmp.name) / "public"
        GEN_PAGES.build_site(str(root), str(self.public), {})

    def test_icons_are_copied_to_the_site_root(self):
        script_dir = Path(GEN_PAGES.__file__).parent
        for icon in GEN_PAGES.SITE_ICONS:
            with self.subTest(icon=icon):
                self.assertEqual(
                    (script_dir / icon).read_bytes(),
                    (self.public / icon).read_bytes(),
                )

    def test_icons_are_transparent_images(self):
        script_dir = Path(GEN_PAGES.__file__).parent
        ico = (script_dir / GEN_PAGES.FAVICON_ICO).read_bytes()
        self.assertEqual(b"\x00\x00\x01\x00", ico[:4])
        for png in (GEN_PAGES.FAVICON_PNG, GEN_PAGES.APPLE_TOUCH_ICON):
            with self.subTest(png=png):
                data = (script_dir / png).read_bytes()
                self.assertEqual(b"\x89PNG\r\n\x1a\n", data[:8])
                # IHDR colour type 6: RGBA, so the corners stay transparent.
                self.assertEqual(6, data[25])

    def test_pages_link_the_icons_relative_to_their_directory(self):
        home = (self.public / "index.html").read_text(encoding="utf-8")
        page = (self.public / "docs/a.md/index.html").read_text(encoding="utf-8")

        self.assertIn('<link rel="icon" href="favicon.ico"', home)
        self.assertIn('<link rel="icon" href="../../favicon.ico"', page)
        self.assertIn('href="../../favicon.png" type="image/png"', page)
        self.assertIn(
            '<link rel="apple-touch-icon" href="../../apple-touch-icon.png">', page
        )


class SeoTests(unittest.TestCase):
    """Description, canonical URL, Open Graph tags, sitemap and robots.txt."""

    def build(self, env):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "README.md").write_text(
            "# Home\n\n[![b](b.png)](x.md)\n\nThe `<home>` & intro.\n\n"
            "![Demo](dist/hyprland.webp)\n",
            encoding="utf-8",
        )
        (root / "x.md").write_text("# X\n", encoding="utf-8")
        (root / "b.png").write_bytes(b"png")
        (root / "dist").mkdir()
        (root / "dist/hyprland.webp").write_bytes(b"webp")
        (root / "docs/a b.md").write_text("# A\n\n" + "word " * 60, encoding="utf-8")
        public = Path(tmp.name) / "public"
        GEN_PAGES.build_site(str(root), str(public), env)
        return public

    def test_site_url_comes_from_site_url_then_gitlab(self):
        url = GEN_PAGES.site_url_from_env

        self.assertEqual(url({"SITE_URL": "https://a.io/d"}), "https://a.io/d/")
        self.assertEqual(
            url({"SITE_URL": "https://a.io/", "CI_PAGES_URL": "https://b.io"}),
            "https://a.io/",
        )
        self.assertEqual(url({"CI_PAGES_URL": "https://b.io/d/"}), "https://b.io/d/")
        self.assertIsNone(url({}))
        self.assertIsNone(url({"SITE_URL": "javascript:alert(1)"}))

    def test_description_skips_badges_and_is_cut_at_a_word(self):
        describe = GEN_PAGES.page_description

        self.assertEqual(
            describe(
                '<p><a href="x"><img alt="b" src="b"></a></p><p>Intro <b>text</b>.</p>'
            ),
            "Intro text.",
        )
        long = describe("<p>" + "word " * 60 + "</p>")
        self.assertLessEqual(len(long), GEN_PAGES.DESCRIPTION_LENGTH)
        self.assertTrue(long.endswith("word..."))
        self.assertIsNone(describe("<h1>Only a title</h1>"))

    def test_page_head_has_description_canonical_and_open_graph(self):
        public = self.build({"SITE_URL": "https://example.org/dotfiles"})
        home = (public / "index.html").read_text(encoding="utf-8")
        page = (public / "docs/a b.md/index.html").read_text(encoding="utf-8")

        self.assertIn(
            '<meta name="description" content="The &lt;home&gt; &amp; intro.">', home
        )
        self.assertIn(
            '<link rel="canonical" href="https://example.org/dotfiles/">', home
        )
        self.assertIn(
            '<link rel="canonical" href="https://example.org/dotfiles/docs/a%20b.md/">',
            page,
        )
        self.assertIn('<meta property="og:title" content="A">', page)
        self.assertIn(
            '<meta property="og:image" '
            'content="https://example.org/dotfiles/dist/hyprland.webp">',
            page,
        )
        self.assertIn('<meta name="twitter:card" content="summary_large_image">', page)

    def test_sitemap_and_robots_list_every_page(self):
        public = self.build({"SITE_URL": "https://example.org/dotfiles/"})
        sitemap = (public / "sitemap.xml").read_text(encoding="utf-8")

        self.assertEqual(
            re.findall(r"<loc>(.*?)</loc>", sitemap),
            [
                "https://example.org/dotfiles/",
                "https://example.org/dotfiles/docs/a%20b.md/",
                "https://example.org/dotfiles/x.md/",
            ],
        )
        self.assertIn(
            "Sitemap: https://example.org/dotfiles/sitemap.xml",
            (public / "robots.txt").read_text(encoding="utf-8"),
        )

    def test_local_build_has_no_absolute_url_and_no_sitemap(self):
        public = self.build({})
        home = (public / "index.html").read_text(encoding="utf-8")

        self.assertFalse((public / "sitemap.xml").exists())
        self.assertFalse((public / "robots.txt").exists())
        self.assertNotIn("canonical", home)
        self.assertNotIn("og:image", home)
        self.assertIn('<meta name="twitter:card" content="summary">', home)
        self.assertIn('<meta name="description" content=', home)


class ThemeMenuTests(unittest.TestCase):
    """The Theme menu at the right end of the navbar picks Light, Dark or Auto."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "repo"
        root.mkdir()
        (root / "README.md").write_text("# Home\n", encoding="utf-8")
        public = Path(tmp.name) / "public"
        GEN_PAGES.build_site(str(root), str(public), {})
        self.page = (public / "index.html").read_text(encoding="utf-8")

    def test_theme_is_set_before_the_stylesheets_load(self):
        head = self.page.split("</head>", 1)[0]

        self.assertIn(GEN_PAGES.THEME_INIT_JS, head)
        self.assertLess(head.index(GEN_PAGES.THEME_INIT_JS), head.index("<link"))

    def test_theme_menu_is_the_last_menu_item(self):
        menu = self.page.split('<ul class="navbar-nav ms-auto">', 1)[1]
        menu = menu.split("</nav>", 1)[0]

        last_item = menu[menu.rindex('<li class="nav-item') :]
        self.assertTrue(last_item.startswith(GEN_PAGES.theme_menu()))
        choices = re.findall(r'data-theme-choice="(\w+)"', menu)
        self.assertEqual(choices, ["light", "dark", "auto"])

    def test_choices_and_button_show_icons(self):
        menu = GEN_PAGES.theme_menu()

        for choice in GEN_PAGES.THEME_CHOICES:
            with self.subTest(choice=choice):
                icon = GEN_PAGES.THEME_ICONS[choice]
                self.assertIn(
                    f'data-theme-choice="{choice}" aria-pressed="false">{icon}',
                    menu,
                )
        # Auto is the default, until the script shows the saved choice.
        self.assertIn(
            f'<span class="theme-current">{GEN_PAGES.THEME_ICONS["auto"]}</span>',
            menu,
        )
        self.assertIn(".theme-current", GEN_PAGES.THEME_MENU_JS)
        self.assertNotIn(">Theme<", menu)

    def test_dropdowns_open_on_hover_only_with_a_mouse(self):
        css = (Path(GEN_PAGES.__file__).parent / "style.css").read_text(
            encoding="utf-8"
        )
        hover = css.split("@media (hover: hover) and (min-width: 768px) {", 1)[1]

        self.assertIn(
            ".navbar .dropdown:hover > .dropdown-menu", hover.split("}", 1)[0]
        )

    def test_menu_script_saves_the_choice_and_follows_the_desktop(self):
        self.assertIn(GEN_PAGES.THEME_MENU_JS, self.page)
        self.assertIn("localStorage.setItem('theme'", GEN_PAGES.THEME_MENU_JS)
        self.assertIn("addEventListener('change'", GEN_PAGES.THEME_MENU_JS)


class MinifyHtmlTests(unittest.TestCase):
    def test_space_between_inline_elements_is_kept(self):
        html = GEN_PAGES.minify_html(
            "<p><strong>Maintainer:</strong> <a href='x'>me</a></p>"
        )

        self.assertIn("</strong> <a", html)

    def test_whitespace_inside_pre_is_kept(self):
        html = GEN_PAGES.minify_html("<div>\n  <pre>a\n  b</pre>\n</div>")

        self.assertIn("<pre>a\n  b</pre>", html)


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

        for url in ("https://example.org/a.md", "#local", "mailto:a@b.c", "//h/x"):
            self.assertEqual(self.rewrite(site, url), url)
        self.assertEqual(site.missing_links, [])

    def test_absolute_link_resolves_from_the_repository_root(self):
        site = self.site()

        self.assertEqual(
            self.rewrite(site, "/docs/b.md#part"), "../b.md/index.html#part"
        )
        self.assertEqual(self.rewrite(site, "/README.md"), "../../index.html")

    def test_missing_absolute_link_is_reported(self):
        site = self.site()

        self.assertEqual(self.rewrite(site, "/nope.md"), "/nope.md")
        self.assertEqual(site.missing_links, [("docs/a.md", "/nope.md")])

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


def nav_shape(nodes):
    """Reduce menu entries to nested (label, source, children) tuples."""
    return [(n.label, n.source, nav_shape(n.children)) for n in nodes]


class NavTreeTests(unittest.TestCase):
    """build_nav_tree: the menu mirrors the tree of the Markdown files."""

    def setUp(self):
        for name, value in {
            "SITE_NAV": [("Docs", "docs/")],
            "NAV_LABELS": {"docs/roles": "Roles"},
            "NAV_EXCLUDE": ["docs/roles/*/files/*"],
        }.items():
            patcher = mock.patch.object(GEN_PAGES, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def tree(self, sources, titles=None):
        return nav_shape(GEN_PAGES.build_nav_tree(sources, titles or {}))

    def test_directory_section_mirrors_the_tree(self):
        sources = [
            "docs/README.md",
            "docs/PLAYBOOKS.md",
            "docs/roles/web/README.md",
            "docs/roles/db/README.md",
        ]
        titles = {"docs/PLAYBOOKS.md": "Playbooks", "docs/roles/db/README.md": "db"}

        self.assertEqual(
            self.tree(sources, titles),
            [
                (
                    "Docs",
                    None,
                    [
                        ("Overview", "docs/README.md", []),
                        ("Playbooks", "docs/PLAYBOOKS.md", []),
                        (
                            "Roles",
                            None,
                            [
                                ("db", "docs/roles/db/README.md", []),
                                ("web", "docs/roles/web/README.md", []),
                            ],
                        ),
                    ],
                )
            ],
        )

    def test_excluded_pages_stay_out_of_the_menu(self):
        sources = ["docs/roles/web/README.md", "docs/roles/web/files/zsh/README.md"]

        self.assertEqual(
            self.tree(sources),
            [("Docs", None, [("Roles", None, [("web", sources[0], [])])])],
        )

    def test_directory_with_a_readme_links_it_above_its_children(self):
        sources = ["docs/guide/README.md", "docs/guide/setup.md"]

        self.assertEqual(
            self.tree(sources, {"docs/guide/README.md": "The guide"}),
            [
                (
                    "Docs",
                    None,
                    [("The guide", sources[0], [("setup", sources[1], [])])],
                )
            ],
        )

    def test_directories_without_pages_are_folded(self):
        sources = ["docs/a/b/c/one.md", "docs/a/b/c/two.md"]

        self.assertEqual(
            self.tree(sources),
            [
                (
                    "Docs",
                    None,
                    [
                        (
                            "a/b/c",
                            None,
                            [("one", sources[0], []), ("two", sources[1], [])],
                        )
                    ],
                )
            ],
        )

    def test_folding_stops_above_a_directory_with_a_readme(self):
        sources = ["docs/a/b/README.md"]

        self.assertEqual(
            self.tree(sources),
            [("Docs", None, [("a", None, [("b", sources[0], [])])])],
        )

    def test_pages_come_before_directories_sorted_by_label(self):
        sources = ["docs/zeta/x.md", "docs/beta.md", "docs/Alpha.md"]

        self.assertEqual(
            [entry[0] for entry in self.tree(sources)[0][2]],
            ["Alpha", "beta", "zeta"],
        )

    def test_label_prefers_nav_labels_then_heading_then_file_name(self):
        sources = ["docs/a.md", "docs/b.md", "docs/c.md"]
        titles = {"docs/a.md": "Heading A", "docs/b.md": "Heading B"}

        with mock.patch.object(GEN_PAGES, "NAV_LABELS", {"docs/a.md": "Label A"}):
            labels = [entry[0] for entry in self.tree(sources, titles)[0][2]]

        self.assertEqual(labels, ["c", "Heading B", "Label A"])

    def test_page_and_group_sections_skip_missing_pages(self):
        nav = [
            ("Home", "README.md"),
            ("Gone", "gone.md"),
            ("CI", ("ci/a.md", "ci/missing.md")),
            ("Empty", "empty/"),
        ]
        with mock.patch.object(GEN_PAGES, "SITE_NAV", nav):
            tree = self.tree(["README.md", "ci/a.md"])

        self.assertEqual(
            tree,
            [("Home", "README.md", []), ("CI", None, [("a", "ci/a.md", [])])],
        )


class BuildNavTests(unittest.TestCase):
    """build_nav: the menu HTML of one page."""

    def setUp(self):
        self.nav = [
            GEN_PAGES.NavNode("Home", "README.md"),
            GEN_PAGES.NavNode(
                "Docs",
                None,
                [
                    GEN_PAGES.NavNode("Overview", "docs/README.md"),
                    GEN_PAGES.NavNode(
                        "<Roles>",
                        None,
                        [GEN_PAGES.NavNode("web", "docs/roles/web/README.md")],
                    ),
                ],
            ),
        ]
        self.pages = {
            source: GEN_PAGES.page_output_path(source)
            for source in ("README.md", "docs/README.md", "docs/roles/web/README.md")
        }

    def menu(self, source):
        return GEN_PAGES.build_nav(self.nav, self.pages, source)[1]

    def test_links_are_relative_to_the_page(self):
        page = self.pages["docs/roles/web/README.md"]

        for href in re.findall(
            r'href="([^"#]+)"', self.menu("docs/roles/web/README.md")
        ):
            with self.subTest(href=href):
                target = posixpath.normpath(
                    posixpath.join(posixpath.dirname(page), href)
                )
                self.assertIn(target, self.pages.values())

    def test_section_of_a_deep_page_is_active(self):
        html = self.menu("docs/roles/web/README.md")

        self.assertIn('class="nav-link dropdown-toggle active"', html)
        self.assertIn(
            '<a class="dropdown-item active" aria-current="page" href="index.html">'
            "web</a>",
            html,
        )
        self.assertNotIn('class="nav-link active"', html)

    def test_page_outside_a_section_leaves_it_inactive(self):
        html = self.menu("README.md")

        self.assertIn('class="nav-link dropdown-toggle"', html)
        self.assertIn('<a class="nav-link active" aria-current="page"', html)

    def test_labels_are_escaped(self):
        html = self.menu("README.md")

        self.assertIn("&lt;Roles&gt;", html)
        self.assertNotIn("<Roles>", html)

    def test_long_submenu_uses_two_columns(self):
        roles = self.nav[1].children[1]
        roles.children = [
            GEN_PAGES.NavNode(f"r{i}", "docs/roles/web/README.md")
            for i in range(GEN_PAGES.NAV_COLUMNS_MIN + 1)
        ]

        html = self.menu("README.md")

        self.assertIn('class="nav-sub nav-columns"', html)
        self.assertIn("dropdown-menu-wide", html)

    def test_short_submenu_keeps_one_column(self):
        html = self.menu("README.md")

        self.assertNotIn("nav-columns", html)
        self.assertNotIn("dropdown-menu-wide", html)


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

    def test_link_to_a_missing_heading_is_reported(self):
        self.write("README.md", "# Home\n\n## Setup\n\n[ok](#setup) [gone](#nope)\n")
        self.write(
            "docs/a.md", "# A\n\n[ok](../README.md#setup) [gone](../README.md#x)\n"
        )

        site = GEN_PAGES.build_site(str(self.root), str(self.public), {})

        self.assertEqual(
            sorted(site.missing_links),
            [("README.md", "#nope"), ("docs/a.md", "../README.md#x")],
        )

    def test_unchanged_asset_is_not_copied_again(self):
        (self.root / "docs/shot.png").write_bytes(b"img")
        self.write("docs/a.md", "# A\n\n![s](shot.png)\n")
        GEN_PAGES.build_site(str(self.root), str(self.public), {})
        copied = self.public / "docs/shot.png"
        os.utime(copied, (0, 0))

        GEN_PAGES.build_site(str(self.root), str(self.public), {})

        self.assertEqual(copied.stat().st_mtime, 0)

    def test_cdn_resources_are_pinned_with_integrity(self):
        GEN_PAGES.build_site(str(self.root), str(self.public), {})
        html = (self.public / "index.html").read_text(encoding="utf-8")

        tags = re.findall(r"<(?:link|script)\b[^>]*https://[^>]*>", html)
        self.assertEqual(len(tags), 5)
        for tag in tags:
            with self.subTest(tag=tag):
                self.assertRegex(tag, r'integrity="sha384-[A-Za-z0-9+/=]{64}"')
                self.assertIn('crossorigin="anonymous"', tag)


class BuildPagesScriptTests(unittest.TestCase):
    """scripts/ci/build_pages.sh when the markdown module is missing."""

    def run_script(self, extra_env):
        with tempfile.TemporaryDirectory() as tmp:
            # A python3 without the markdown module, first on PATH.
            fake = Path(tmp) / "python3"
            fake.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            fake.chmod(0o755)
            env = {k: v for k, v in os.environ.items() if k != "CI"}
            env.update(extra_env, PATH=f"{tmp}:{os.environ['PATH']}")
            return subprocess.run(
                ["sh", str(SCRIPT_PATH.with_name("build_pages.sh"))],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )

    def test_local_hook_skips_without_failing(self):
        self.assertEqual(self.run_script({}).returncode, 0)

    def test_ci_job_fails(self):
        result = self.run_script({"CI": "true"})

        self.assertEqual(result.returncode, 1)
        self.assertIn("markdown", result.stderr)


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

    def test_every_menu_section_has_pages(self):
        sources = GEN_PAGES.discover_markdown(str(REPO_ROOT))
        sections = {node.label for node in GEN_PAGES.build_nav_tree(sources, {})}

        self.assertEqual(sections, {label for label, _ in GEN_PAGES.SITE_NAV})

    def test_menu_lists_the_ansible_playbooks_and_roles(self):
        sources = GEN_PAGES.discover_markdown(str(REPO_ROOT))
        ansible = next(
            node
            for node in GEN_PAGES.build_nav_tree(sources, {})
            if node.label == "Ansible"
        )
        listed = {source for _, source, _ in nav_shape(ansible.children)}
        roles = next(node for node in ansible.children if node.label == "Roles")

        self.assertIn("ansible/PLAYBOOKS.md", listed)
        self.assertEqual(
            {node.source for node in roles.children},
            {
                source
                for source in sources
                if re.fullmatch(r"ansible/roles/[^/]+/README\.md", source)
            },
        )

    def test_published_site_has_no_broken_relative_link(self):
        for env in (GITLAB_ENV, {}):
            with self.subTest(ci=bool(env)):
                site, public = self.build(env)

                self.assertEqual(site.missing_links, [])
                self.assertEqual(broken_relative_links(public), [])


if __name__ == "__main__":
    unittest.main()
