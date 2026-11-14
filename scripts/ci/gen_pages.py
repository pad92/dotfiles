import filecmp
import fnmatch
import html as _html
import os
import posixpath
import re
import shutil
import subprocess
import sys
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from urllib.parse import quote, unquote

import markdown

try:
    from pygments import highlight as _pyg_highlight
    from pygments.formatters.html import HtmlFormatter as _PygHtmlFormatter
    from pygments.lexers import get_lexer_by_name as _pyg_lexer
    from pygments.util import ClassNotFound as _PygClassNotFound

    _HAVE_PYGMENTS = True
except ImportError:  # pragma: no cover - pygments is optional
    _HAVE_PYGMENTS = False

# Every Markdown file of the repository becomes a page. Its output path mirrors
# the source path (`docs/x.md` -> `docs/x.md/index.html`) so relative links
# written for the forge keep the same shape on the published site.
HOME_SOURCE = "README.md"
STYLE_FILE = "style.css"
NOJEKYLL_FILE = ".nojekyll"
SITEMAP_FILE = "sitemap.xml"
ROBOTS_FILE = "robots.txt"
# Public URL of the site: GitLab Pages under its own domain, so robots.txt sits
# at the root of the host. `pad92.gitlab.io/dotfiles` redirects there, and the
# GitHub copy points its canonical URLs there too. `SITE_URL` overrides it.
DEFAULT_SITE_URL = "https://dotfiles.depad.fr/"
# Icons of the site, kept next to this script and published at the site root:
# the .ico for old browsers, a 192 px PNG for the others, 180 px for iOS.
FAVICON_ICO = "favicon.ico"
FAVICON_PNG = "favicon.png"
APPLE_TOUCH_ICON = "apple-touch-icon.png"
SITE_ICONS = (FAVICON_ICO, FAVICON_PNG, APPLE_TOUCH_ICON)

# actions/upload-pages-artifact drops .git and .github from the deployed
# tarball, so pages from .github/ are published under github/ instead.
RENAMED_PREFIXES = {".github/": "github/"}

# Directories never scanned when Git is unavailable (CI images without git).
SKIPPED_DIRS = {
    ".ansible",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "node_modules",
    "public",
    "venv",
}

# Linked local files with these extensions are copied next to the pages;
# any other linked file points to the repository browser instead.
ASSET_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}

# Top-level sections of the site navigation menu, in order: (label, target).
# A target is one page, a tuple of pages shown as a dropdown, or a directory
# (ending with "/") whose pages become a dropdown that mirrors the tree.
SITE_NAV: list[tuple[str, str | tuple[str, ...]]] = [
    ("Home", HOME_SOURCE),
    ("Ansible", "ansible/"),
    ("Arch Linux", "dist/arch/"),
    ("CI", (".github/workflows/README.md", ".gitlab/README.md")),
    ("Changelog", "CHANGELOG.md"),
]
# Menu labels that replace a page's first heading or a directory's name.
NAV_LABELS = {
    ".github/workflows/README.md": "GitHub Actions",
    ".gitlab/README.md": "GitLab CI",
    "ansible/roles": "Roles",
    "dist/arch/dns-migration.md": "DNS migration",
    "dist/arch/install.md": "Installation",
}
# Pages left out of the menu (fnmatch patterns, `*` also matches `/`). They
# are still published and reachable through links. Role payload files are
# installed into the home directory, they are not documentation of the repo.
NAV_EXCLUDE = ["ansible/roles/*/files/*"]
# The README of a directory is its page in the menu.
NAV_INDEX = "README.md"
# A submenu with more entries than this is laid out in two columns.
NAV_COLUMNS_MIN = 10
SITE_TITLE = "Pad's Dotfiles"
# Preview image of shared links (Open Graph), when the build publishes it.
SITE_IMAGE = "dist/hyprland.webp"
# Search engines show about 160 characters of a description.
DESCRIPTION_LENGTH = 160

# CDN resources, pinned with Subresource Integrity: a changed file (e.g. a
# moved Git tag behind cdn.jsdelivr.net/gh/) is refused by the browser.
# Recompute a hash with:
#   curl -fsSL URL | openssl dgst -sha384 -binary | openssl base64 -A
CDN_INTEGRITY = {
    "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css": (
        "sha384-9ndCyUaIbzAi2FUVXJi0CjmCapSmO7SnpJef0486qhLnuZ2cdeRhO02iuK6FUUVM"  # pragma: allowlist secret
    ),
    "https://cdn.jsdelivr.net/gh/afeld/bootstrap-toc@v1.0.1/dist/bootstrap-toc.min.css": (
        "sha384-oJyFk/zeMJXNIGMVvmH262FT6dbSYss66WJHHgp1RlUk4/LfONQTzkAsHHwfcqat"  # pragma: allowlist secret
    ),
    "https://code.jquery.com/jquery-3.7.1.slim.min.js": (
        "sha384-5AkRS45j4ukf+JbWAfHL8P4onPA9p0KwwP7pUdjSQA3ss9edbJUJc/XcYAiheSSz"  # pragma: allowlist secret
    ),
    "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js": (
        "sha384-geWF76RCwLtnZ8qwWowPQNguL3RmwHVBC9FhGdlKrxdiJJigb/j/68SIy3Te4Bkz"  # pragma: allowlist secret
    ),
    "https://cdn.jsdelivr.net/gh/afeld/bootstrap-toc@v1.0.1/dist/bootstrap-toc.min.js": (
        "sha384-OGf04BRlCdmgZXHhCupHT3BIkznbahjfhX8DKSIEXyU9PvSO0/8iMiiVJPcA5vi7"  # pragma: allowlist secret
    ),
}


def cdn_tags(extension: str) -> str:
    """Return the <link> or <script> tags of the CDN_INTEGRITY files of extension."""
    tag = {
        ".css": '<link rel="stylesheet" href="{url}" integrity="{sri}" crossorigin="anonymous">',
        ".js": '<script src="{url}" integrity="{sri}" crossorigin="anonymous"></script>',
    }[extension]
    return "\n".join(
        tag.format(url=url, sri=sri)
        for url, sri in CDN_INTEGRITY.items()
        if url.endswith(extension)
    )


_URL_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
# Only real tags are matched: Markdown escapes `<` in code spans, so an
# `<img src="...">` sample shown as code is never taken for a link.
_LINK_TAG_RE = re.compile(r"<(?:a|img|source)\b[^>]*>", re.IGNORECASE)
_LINK_ATTR_RE = re.compile(
    r"""(\s(?:href|src)\s*=\s*)(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE
)
_HTML_HEADING_RE = re.compile(r"<h[1-6]\b[^>]*>(.*?)</h[1-6]>", re.DOTALL)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_OPEN_TAG_RE = re.compile(r"<[A-Za-z][^>]*>")
_HTML_ANCHOR_RE = re.compile(r"""\s(?:id|name)\s*=\s*(?:"([^"]*)"|'([^']*)')""")
# A fence may sit in a blockquote: (quote markers, indent, fence, info string).
_FENCE_OPEN_RE = re.compile(r"^((?:[ \t]*>[ \t]?)*)([ \t]*)(`{3,}|~{3,})(.*)$")
_QUOTE_MARKER_RE = re.compile(r"[ \t]*>[ \t]?")
# GitHub drops every character but letters, digits, `_`, `-` and spaces.
_SLUG_DROP_RE = re.compile(r"[^\w\- ]")
_FENCE_LANG_RE = re.compile(r"[\w+-]+")
# GitLab's table-of-contents markers, honoured only alone on their line.
_TOC_MARKER_RE = re.compile(r"^[ \t]*\[\[(?:TOC|_TOC_)\]\][ \t]*$", re.MULTILINE)


def published_path(path: str) -> str:
    """Return where a repository file is published, relative to the site root."""
    for prefix, replacement in RENAMED_PREFIXES.items():
        if path.startswith(prefix):
            return replacement + path[len(prefix) :]
    return path


def page_output_path(source: str) -> str:
    """Return the page path, relative to the site root, for a Markdown source."""
    if source == HOME_SOURCE:
        return "index.html"
    return f"{published_path(source)}/index.html"


@dataclass
class NavNode:
    """One menu entry: a page (source) or a heading (no source), with children."""

    label: str
    source: str | None = None
    children: list["NavNode"] = field(default_factory=list)

    def contains(self, source: str) -> bool:
        """Return whether source is this entry's page or one of its children's."""
        return self.source == source or any(c.contains(source) for c in self.children)


def nav_excluded(source: str) -> bool:
    return any(fnmatch.fnmatchcase(source, pattern) for pattern in NAV_EXCLUDE)


def _label_key(node: NavNode) -> str:
    return node.label.casefold()


def page_nav_label(source: str, titles: Mapping[str, str | None]) -> str:
    """Use NAV_LABELS, then the page's first heading, then its file name.

    A README falls back to the name of its directory.
    """
    directory, name = posixpath.split(source)
    if name == NAV_INDEX and directory:
        fallback = posixpath.basename(directory)
    else:
        fallback = posixpath.splitext(name)[0]
    return NAV_LABELS.get(source) or titles.get(source) or fallback


def directory_nav(
    directory: str, sources: Collection[str], titles: Mapping[str, str | None]
) -> list[NavNode]:
    """Return the menu entries below directory (a path ending with "/").

    Pages of the directory come first, then its subdirectories, each sorted by
    label. The directory's own README is left to the caller.
    """
    pages = []
    subdirs: dict[str, list[str]] = {}
    for source in sources:
        if not source.startswith(directory):
            continue
        rest = source[len(directory) :]
        if "/" in rest:
            subdirs.setdefault(rest.split("/", 1)[0], []).append(source)
        elif rest != NAV_INDEX:
            pages.append(NavNode(page_nav_label(source, titles), source))
    dirs = [
        _directory_node(f"{directory}{name}/", name, below, titles)
        for name, below in subdirs.items()
    ]
    return sorted(pages, key=_label_key) + sorted(dirs, key=_label_key)


def _directory_node(
    directory: str, name: str, sources: list[str], titles: Mapping[str, str | None]
) -> NavNode:
    """Return the entry of a subdirectory: its README, or a heading without one.

    A directory with no page of its own and a single subdirectory, itself
    without a README, is folded into it (`a/b`), so the menu shows no empty
    levels. A directory named in NAV_LABELS is never folded.
    """
    while directory.rstrip("/") not in NAV_LABELS:
        rests = [source[len(directory) :] for source in sources]
        firsts = {rest.split("/", 1)[0] for rest in rests}
        if any("/" not in rest for rest in rests) or len(firsts) != 1:
            break
        sub = firsts.pop()
        if f"{directory}{sub}/{NAV_INDEX}" in sources:
            break
        directory, name = f"{directory}{sub}/", f"{name}/{sub}"
    index = directory + NAV_INDEX
    page = index if index in sources else None
    label = (
        NAV_LABELS.get(directory.rstrip("/"))
        or (page and page_nav_label(page, titles))
        or name
    )
    return NavNode(label, page, directory_nav(directory, sources, titles))


def build_nav_tree(
    sources: Collection[str], titles: Mapping[str, str | None]
) -> list[NavNode]:
    """Return the top-level menu entries of SITE_NAV that have pages.

    titles maps a source to its first heading (None without one).
    """
    nodes = []
    for label, target in SITE_NAV:
        if isinstance(target, tuple):
            children = [
                NavNode(page_nav_label(source, titles), source)
                for source in target
                if source in sources
            ]
            if children:
                nodes.append(NavNode(label, None, children))
        elif target.endswith("/"):
            visible = [
                source
                for source in sources
                if source.startswith(target) and not nav_excluded(source)
            ]
            children = directory_nav(target, visible, titles)
            if target + NAV_INDEX in visible:
                children.insert(0, NavNode("Overview", target + NAV_INDEX))
            if children:
                nodes.append(NavNode(label, None, children))
        elif target in sources:
            nodes.append(NavNode(label, target))
    return nodes


def build_nav(
    nodes: list[NavNode], pages: Mapping[str, str], source: str
) -> tuple[str, str]:
    """Return (brand_href, nav_items_html) for the page of source.

    Links are relative to the page, so the site works under a subpath (e.g.
    project GitHub/GitLab Pages served from /<repo>/). The section holding the
    page is highlighted and the page's own entry is marked as current.
    """
    cur_dir = posixpath.dirname(pages[source]) or "."

    def href(target: str) -> str:
        path = quote(posixpath.relpath(pages[target], cur_dir), safe="/")
        return _html.escape(path)

    def link(node: NavNode, css: str) -> str:
        assert node.source is not None
        label = _html.escape(node.label)
        if node.source == source:
            return (
                f'<a class="{css} active" aria-current="page" '
                f'href="{href(node.source)}">{label}</a>'
            )
        return f'<a class="{css}" href="{href(node.source)}">{label}</a>'

    def entry(node: NavNode) -> str:
        if node.source is not None:
            head = link(node, "dropdown-item")
        else:
            head = f'<span class="dropdown-header">{_html.escape(node.label)}</span>'
        if node.children:
            columns = " nav-columns" if len(node.children) > NAV_COLUMNS_MIN else ""
            subs = "".join(entry(child) for child in node.children)
            head += f'<ul class="nav-sub{columns}">{subs}</ul>'
        return f"<li>{head}</li>"

    def wide(node: NavNode) -> bool:
        return len(node.children) > NAV_COLUMNS_MIN or any(
            wide(child) for child in node.children
        )

    items = []
    for node in nodes:
        if not node.children:
            items.append(f'<li class="nav-item">{link(node, "nav-link")}</li>')
            continue
        active = " active" if node.contains(source) else ""
        menu = "dropdown-menu dropdown-menu-end"
        if any(wide(child) for child in node.children):
            menu += " dropdown-menu-wide"
        entries = "".join(entry(child) for child in node.children)
        items.append(
            f'<li class="nav-item dropdown">'
            f'<a class="nav-link dropdown-toggle{active}" href="#" role="button" '
            f'data-bs-toggle="dropdown" aria-expanded="false">'
            f"{_html.escape(node.label)}</a>"
            f'<ul class="{menu}">{entries}</ul></li>'
        )

    brand_href = posixpath.relpath("index.html", cur_dir)
    return brand_href, "\n".join(items)


def minify_css(css):
    """Lightweight CSS minifier: strip comments and redundant whitespace."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{}:;,>])\s*", r"\1", css)
    css = css.replace(";}", "}")
    return css.strip()


def minify_html(html):
    """Collapse whitespace runs in HTML to one space, except in blocks where
    whitespace is significant (code, scripts, inline styles)."""
    protected = []

    def _stash(match):
        protected.append(match.group(0))
        return f"\x00{len(protected) - 1}\x00"

    html = re.sub(
        r"<(pre|code|script|style|textarea)\b[^>]*>.*?</\1>",
        _stash,
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # Whitespace between tags is collapsed, not removed: between inline
    # elements (`<strong>a</strong> <a>`) it is a visible space.
    html = re.sub(r"\s+", " ", html).strip()

    for i, block in enumerate(protected):
        html = html.replace(f"\x00{i}\x00", block)
    return html


def write_if_changed(path, content):
    """Write generated text only when its contents differ."""
    try:
        with open(path, "r", encoding="utf-8") as current:
            if current.read() == content:
                return False
    except FileNotFoundError:
        pass

    with open(path, "w", encoding="utf-8") as output:
        output.write(content)
    return True


def get_alert_resources(alert_type):
    # SVG icons from Octicons/Pajamas
    icons = {
        "NOTE": (
            '<svg class="octicon octicon-info" viewBox="0 0 16 16" version="1.1" width="16" height="16" aria-hidden="true">'
            '<path d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8Zm8-3a1 1 0 1 0 0-2 1 1 0 0 0 0 2Zm3 3H8.75v3.25a.25.25 0 0 0 .25.25h1a.75.75 0 0 1 0 1.5h-3a.75.75 0 0 1 0-1.5h1V6.75A.75.75 0 0 1 7.75 6H11a.75.75 0 0 1 0 1.5Z"></path>'
            "</svg>",
            "Note",
        ),
        "TIP": (
            '<svg class="octicon octicon-light-bulb" viewBox="0 0 16 16" version="1.1" width="16" height="16" aria-hidden="true">'
            '<path d="M8 1.5c-2.363 0-4 1.637-4 4 0 .918.353 1.703.844 2.5a.75.75 0 0 1 .156.467v1.283c0 .338.224.626.549.724l.325.097a.75.75 0 0 1 .526.718v.5a.75.75 0 0 1-.75.75H5a.75.75 0 0 1 0-1.5h.25v-.31L4.85 10.9A2.25 2.25 0 0 1 3.5 8.813V7.218A4.25 4.25 0 0 1 7.25 3h1.5A4.25 4.25 0 0 1 13 7.218v1.595a2.25 2.25 0 0 1-1.35 2.087l-.4 1.205V12.4H11a.75.75 0 0 1 0 1.5h-.25a.75.75 0 0 1-.75-.75v-.5a.75.75 0 0 1 .526-.718l.325-.097a.75.75 0 0 1 .549-.724V8.467a.75.75 0 0 1 .156-.467c.49-.797.843-1.582.843-2.5 0-2.363-1.637-4-4-4ZM5.496 7.42a5.75 5.75 0 0 0-.746-1.92c-.143-.23-.25-.49-.25-.75 0-1.363.937-2.5 2.5-2.5h1.5c1.563 0 2.5 1.137 2.5 2.5 0 .26-.107.52-.25.75-.245.395-.5.852-.746 1.92l-.153.667H6.649l-.153-.667ZM9 15.25a1.25 1.25 0 1 1-2.5 0h2.5Z"></path>'
            "</svg>",
            "Tip",
        ),
        "IMPORTANT": (
            '<svg class="octicon octicon-report" viewBox="0 0 16 16" version="1.1" width="16" height="16" aria-hidden="true">'
            '<path d="M0 1.75C0 .783.783 0 1.75 0h12.5C15.217 0 16 .783 16 1.75v12.5A1.75 1.75 0 0 1 14.25 16H1.75A1.75 1.75 0 0 1 0 14.25ZM1.75-.25a.25.25 0 0 0-.25.25v12.5c0 .138.112.25.25.25h12.5a.25.25 0 0 0 .25-.25V1.75a.25.25 0 0 0-.25-.25ZM8 3.25a.75.75 0 0 1 .75.75v3.25a.75.75 0 0 1-1.5 0V4a.75.75 0 0 1 .75-.75Zm0 7a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z"></path>'
            "</svg>",
            "Important",
        ),
        "WARNING": (
            '<svg class="octicon octicon-alert" viewBox="0 0 16 16" version="1.1" width="16" height="16" aria-hidden="true">'
            '<path d="M6.457 1.047c.66-1.1 2.227-1.1 2.887 0l6.03 10.05c.66 1.1-.124 2.5-1.444 2.5H1.87c-1.32 0-2.104-1.4-1.444-2.5Zm2.127.854a.75.75 0 0 0-1.168 0L1.386 11.95a.75.75 0 0 0 .643 1.135h12.042a.75.75 0 0 0 .643-1.135Zm-1.834 8.6a1 1 0 1 1 2 0 1 1 0 0 1-2 0Zm1.25-4.75a.75.75 0 0 0-1.5 0v2.5a.75.75 0 0 0 1.5 0Z"></path>'
            "</svg>",
            "Warning",
        ),
        "CAUTION": (
            '<svg class="octicon octicon-stop" viewBox="0 0 16 16" version="1.1" width="16" height="16" aria-hidden="true">'
            '<path d="M4.47.22A.75.75 0 0 1 5 0h6c.2 0 .39.08.53.22l4.25 4.25c.14.14.22.33.22.53v6c0 .2-.08.39-.22.53l-4.25 4.25A.75.75 0 0 1 11 16H5a.75.75 0 0 1-.53-.22L.22 11.53A.75.75 0 0 1 0 11V5c0-.2.08-.39.22-.53Zm.8 1.28L1.5 5.25v5.5l3.77 3.77h5.46l3.77-3.77v-5.5L10.73 1.5Z"></path><path d="M8 4a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 8 4Zm0 7a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z"></path>'
            "</svg>",
            "Caution",
        ),
    }
    return icons.get(alert_type, (None, alert_type))


# Gruvbox, like style.css and the Hyprland desktop. The light style applies
# under LIGHT_THEME, as the light block of style.css does.
PYGMENTS_STYLE = "gruvbox-dark"
PYGMENTS_LIGHT_STYLE = "gruvbox-light"
LIGHT_THEME = ':root[data-theme="light"]'

# Theme switcher. THEME_INIT_JS runs in <head>, before the page is drawn, and
# sets data-theme on <html> to "light" or "dark" from the saved choice ("auto"
# by default, which follows the desktop). THEME_MENU_JS drives the
# Light/Dark/Auto entries of the menu, saves the choice in localStorage,
# shows the icon of the choice on the menu button and follows desktop changes
# while the choice is "auto". Without JavaScript the site stays dark.
THEME_CHOICES = ("light", "dark", "auto")
# Icons of the choices, drawn with the text colour: a sun, a crescent moon and
# a half-filled circle.
_ICON = (
    '<svg class="theme-icon" viewBox="0 0 16 16" width="1em" height="1em" '
    'fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{}</svg>'
)
THEME_ICONS = {
    "light": _ICON.format(
        '<circle cx="8" cy="8" r="3"/><path d="M8 1v1.5M8 13.5V15M1 8h1.5'
        "M13.5 8H15M3.05 3.05l1.06 1.06M11.89 11.89l1.06 1.06M3.05 12.95"
        'l1.06-1.06M11.89 4.11l1.06-1.06"/>'
    ),
    "dark": _ICON.format('<path d="M13.5 10A6 6 0 0 1 6 2.5a6 6 0 1 0 7.5 7.5z"/>'),
    "auto": _ICON.format(
        '<circle cx="8" cy="8" r="6.25"/>'
        '<path d="M8 1.75a6.25 6.25 0 0 0 0 12.5z" fill="currentColor"/>'
    ),
}
THEME_INIT_JS = (
    "(function(){var c;try{c=localStorage.getItem('theme')}catch(e){}"
    "if(c!=='light'&&c!=='dark')c='auto';var d=document.documentElement;"
    "d.dataset.themeChoice=c;d.dataset.theme=c==='auto'?"
    "(matchMedia('(prefers-color-scheme: light)').matches?'light':'dark'):c})();"
)
THEME_MENU_JS = (
    "(function(){var d=document.documentElement,"
    "m=matchMedia('(prefers-color-scheme: light)'),"
    "items=document.querySelectorAll('button[data-theme-choice]'),"
    "t=document.querySelector('.theme-menu .theme-current');"
    "function apply(c){d.dataset.themeChoice=c;"
    "d.dataset.theme=c==='auto'?(m.matches?'light':'dark'):c;"
    "items.forEach(function(b){var on=b.dataset.themeChoice===c;"
    "b.classList.toggle('active',on);b.setAttribute('aria-pressed',String(on));"
    "if(on&&t)t.innerHTML=b.querySelector('svg').outerHTML})}"
    "items.forEach(function(b){b.addEventListener('click',function(){"
    "var c=b.dataset.themeChoice;try{localStorage.setItem('theme',c)}catch(e){}"
    "apply(c)})});"
    "m.addEventListener('change',function(){"
    "if(d.dataset.themeChoice==='auto')apply('auto')});"
    "apply(d.dataset.themeChoice||'auto')})();"
)


def theme_menu():
    """The Light/Dark/Auto dropdown, last item of the menu.

    Its button shows the icon of the current choice, Auto until the script
    runs.
    """
    items = "".join(
        f'<li><button class="dropdown-item" type="button" '
        f'data-theme-choice="{choice}" aria-pressed="false">'
        f"{THEME_ICONS[choice]}{choice.capitalize()}</button></li>"
        for choice in THEME_CHOICES
    )
    return (
        '<li class="nav-item dropdown theme-menu">'
        '<button class="nav-link dropdown-toggle" type="button" '
        'data-bs-toggle="dropdown" aria-expanded="false" '
        'aria-label="Colour theme">'
        f'<span class="theme-current">{THEME_ICONS["auto"]}</span></button>'
        f'<ul class="dropdown-menu dropdown-menu-end">{items}</ul></li>'
    )


def pygments_css():
    """Syntax-highlighting colours for `.codehilite`, themed for the dark pages.

    Returns an empty string when Pygments is unavailable (code still renders,
    just without colours). The code box background is left to the themed `pre`
    rule, so only the token colours come from the Pygments style.
    """
    if not _HAVE_PYGMENTS:
        return ""
    dark = _PygHtmlFormatter(style=PYGMENTS_STYLE).get_style_defs(".codehilite")
    light = _PygHtmlFormatter(style=PYGMENTS_LIGHT_STYLE).get_style_defs(
        f"{LIGHT_THEME} .codehilite"
    )
    # The light style leaves some tokens (punctuation, YAML scalars...) to the
    # text colour, but the dark rules for them still match: reset them first.
    token_rule = re.compile(r"^(?:.* )?\.codehilite (\.[\w-]+) \{", re.M)
    dark_only = sorted(set(token_rule.findall(dark)) - set(token_rule.findall(light)))
    reset = (
        ",".join(f"{LIGHT_THEME} .codehilite {token}" for token in dark_only)
        + "{color:inherit;background-color:transparent;font-weight:inherit;"
        + "font-style:inherit;text-decoration:inherit}\n"
        if dark_only
        else ""
    )
    return (
        "\n"
        + dark
        + "\n"
        + reset
        + light
        # Same specificity as the light rule, later: wins over both styles.
        + "\n.codehilite,:root[data-theme] .codehilite{background:transparent}\n"
    )


def render_code_block(code, lang):
    """Render a fenced code block to HTML matching codehilite's `.codehilite`."""
    if _HAVE_PYGMENTS and lang:
        try:
            return _pyg_highlight(
                code, _pyg_lexer(lang), _PygHtmlFormatter(cssclass="codehilite")
            )
        except _PygClassNotFound:
            pass
    cls = f' class="language-{lang}"' if lang else ""
    return f'<div class="codehilite"><pre><code{cls}>{_html.escape(code)}</code></pre></div>'


def stash_code_blocks(text: str, store: list[str]) -> str:
    """Replace fenced code blocks with placeholders and render them ourselves.

    python-markdown's `fenced_code` does not recognise fences nested inside list
    items (it turns them into inline code), so we extract every fenced block
    here, dedenting by the opening fence's indentation, render it, and reinsert
    the HTML after Markdown conversion (see restore_code_blocks). The
    placeholder keeps the fence's indent so it stays within its list item.

    As in CommonMark, a fence is three or more backticks or tildes, followed by
    an info string whose first word is the language, and it is closed only by
    a run of the same character at least as long: a ```` fence can show a
    ``` fence as code. A fence inside a blockquote (alerts included) has its
    `>` markers removed from the code and kept before the placeholder. A fence
    never closed, or whose blockquote ends first, is left to python-markdown.
    """
    lines = text.split("\n")
    output = []
    i = 0
    while i < len(lines):
        opening = _FENCE_OPEN_RE.match(lines[i])
        end = _closing_fence_index(lines, i, opening) if opening else None
        if opening is None or end is None:
            output.append(lines[i])
            i += 1
            continue
        quote, indent, _fence, info = opening.groups()
        depth = quote.count(">")
        n = len(indent)
        body = [_strip_quote(line, depth) or "" for line in lines[i + 1 : end]]
        code = "\n".join(line[n:] if line[:n].strip() == "" else line for line in body)
        lang_match = _FENCE_LANG_RE.match(info.strip())
        store.append(render_code_block(code, lang_match.group(0) if lang_match else ""))
        output.append(quote + indent + code_block_token(len(store) - 1))
        i = end + 1
    return "\n".join(output)


def _strip_quote(line: str, depth: int) -> str | None:
    """Return line without its first depth `>` markers, None if it has fewer."""
    pos = 0
    for _ in range(depth):
        marker = _QUOTE_MARKER_RE.match(line, pos)
        if marker is None:
            return None
        pos = marker.end()
    return line[pos:]


def _closing_fence_index(
    lines: list[str], start: int, opening: re.Match[str]
) -> int | None:
    """Return the index of the line closing the fence opened at start.

    Returns None when the fence is never closed, or when a line without the
    opening's `>` markers ends its blockquote first.
    """
    quote, _indent, fence, info = opening.groups()
    if fence[0] == "`" and "`" in info:
        return None  # Not a fence: a backtick info string has no backtick.
    depth = quote.count(">")
    closing = re.compile(rf"^[ \t]*{re.escape(fence[0])}{{{len(fence)},}}[ \t]*$")
    for j in range(start + 1, len(lines)):
        rest = _strip_quote(lines[j], depth)
        if rest is None:
            return None
        if closing.match(rest):
            return j
    return None


def code_block_token(index: int) -> str:
    return f"xxcodeblock{index}xx"


def restore_code_blocks(html: str, store: list[str]) -> str:
    """Put the stashed code blocks back, dropping any <p> wrapper Markdown added."""
    for i, block in enumerate(store):
        token = code_block_token(i)
        html = html.replace(f"<p>{token}</p>", block).replace(token, block)
    return html


def normalize_nested_list_indentation(text):
    """Adapt compact nested lists without changing unrelated indentation."""
    quote_re = re.compile(r"^((?: {0,3}>[ \t]?)*)(.*)$")
    marker_re = re.compile(r"^( *)(?:[-+*]|\d+[.)])\s+")
    stacks = {}
    normalized = []

    for line in text.split("\n"):
        quote_match = quote_re.match(line)
        quote_prefix, content = quote_match.groups()
        stack = stacks.setdefault(quote_prefix, [])
        marker = marker_re.match(content)

        if marker:
            source_indent = len(marker.group(1))
            while stack and source_indent < stack[-1][0]:
                stack.pop()

            if stack and source_indent == stack[-1][0]:
                output_indent = stack[-1][1]
            elif stack:
                output_indent = stack[-1][1] + 4
                stack.append((source_indent, output_indent))
            else:
                output_indent = source_indent
                stack.append((source_indent, output_indent))

            normalized.append(
                quote_prefix + " " * output_indent + content[source_indent:]
            )
            continue

        if not content.strip():
            normalized.append(line)
            continue

        source_indent = len(content) - len(content.lstrip(" "))
        while len(stack) > 1 and source_indent <= stack[-1][0]:
            stack.pop()

        if stack and source_indent > stack[-1][0]:
            offset = stack[-1][1] - stack[-1][0]
            content = " " * (source_indent + offset) + content[source_indent:]
        elif source_indent == 0:
            stack.clear()

        if not quote_prefix:
            stacks = {"": stack}
        normalized.append(quote_prefix + content)

    return "\n".join(normalized)


class HeadingSlugger:
    """Build heading ids as GitHub does, unique across one page.

    The text is lowercased, punctuation is dropped (accents and other letters
    stay) and each space becomes a hyphen, without merging runs: `A & B` gives
    `a--b`. A repeated id gets `-1`, `-2`... Alerts are rendered in their own
    Markdown pass, so every pass of a page shares one slugger; an alert's
    headings are numbered before the page's, which differs from GitHub only
    when an alert repeats a heading of the page.
    """

    def __init__(self) -> None:
        self.occurrences: dict[str, int] = {}

    def __call__(self, value: str, separator: str) -> str:
        base = _SLUG_DROP_RE.sub("", value.strip().lower()).replace(" ", separator)
        slug = base
        while slug in self.occurrences:
            self.occurrences[base] += 1
            slug = f"{base}{separator}{self.occurrences[base]}"
        self.occurrences[slug] = 0
        return slug


def render_markdown(text: str, slugify: HeadingSlugger | None = None) -> str:
    """Render Markdown using the compact nested-list style used by the docs.

    Heading ids come from slugify, which a page shares between its passes.
    """
    text = normalize_nested_list_indentation(text)
    return markdown.markdown(
        text,
        extensions=["extra", "codehilite", "toc"],
        extension_configs={"toc": {"slugify": slugify or HeadingSlugger()}},
    )


def parse_alerts(text: str, slugify: HeadingSlugger | None = None) -> str:
    """Render GitHub/GitLab alerts (`> [!NOTE]` blockquotes) to HTML.

    Fenced code inside an alert must already be stashed (stash_code_blocks
    handles fences in blockquotes).
    """
    slugify = slugify or HeadingSlugger()
    lines = text.split("\n")
    new_lines = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        match = re.match(
            r"^(\s*)>\s*\[!(TIP|NOTE|WARNING|IMPORTANT|CAUTION)\](?:\s*(.*))?$",
            line,
            re.IGNORECASE,
        )
        if match:
            indent = match.group(1)
            alert_type = match.group(2).upper()
            first_line_content = match.group(3)

            alert_lines = []
            if first_line_content and first_line_content.strip():
                alert_lines.append(first_line_content)

            i += 1
            while i < n:
                next_line = lines[i]
                next_match = re.match(r"^\s*>\s?(.*)$", next_line)
                if next_match:
                    alert_lines.append(next_match.group(1))
                    i += 1
                else:
                    break

            compiled_content = render_markdown("\n".join(alert_lines), slugify)

            icon_svg, title_text = get_alert_resources(alert_type)

            alert_html = (
                f'<div class="markdown-alert markdown-alert-{alert_type.lower()}">\n'
                f'<p class="markdown-alert-title">{icon_svg}{title_text}</p>\n'
                f"{compiled_content}\n"
                f"</div>"
            )

            indented_lines = []
            for segment in alert_html.split("\n"):
                if segment.strip():
                    indented_lines.append(indent + segment)
                else:
                    indented_lines.append(segment)
            alert_html = "\n".join(indented_lines)

            new_lines.append(alert_html)
        else:
            new_lines.append(line)
            i += 1

    return "\n".join(new_lines)


def submodule_paths(root: str) -> set[str]:
    """Return the submodule paths declared in root's .gitmodules, if any."""
    try:
        with open(os.path.join(root, ".gitmodules"), "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return set()
    return {
        posixpath.normpath(path)
        for path in re.findall(r"^\s*path\s*=\s*(.+?)\s*$", text, re.MULTILINE)
    }


def env_for_root_repository() -> dict[str, str]:
    """Return the environment without Git's repository-selecting variables.

    A Git hook run from a linked worktree inherits GIT_DIR; with it, `git -C
    root` would list another repository than the one at root. Raises OSError
    when Git is not installed.
    """
    names = subprocess.run(
        ["git", "rev-parse", "--local-env-vars"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    return {k: v for k, v in os.environ.items() if k not in names}


def discover_markdown(root: str) -> list[str]:
    """List Markdown sources (POSIX paths relative to root), sorted.

    Git is preferred so ignored or untracked local files are not published;
    CI images without Git fall back to a filesystem walk of the clean checkout.
    """
    try:
        listed = subprocess.run(
            ["git", "-C", root, "ls-files", "-z", "--", "*.md"],
            check=True,
            capture_output=True,
            text=True,
            env=env_for_root_repository(),
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        # Submodules are third-party code: git ls-files does not list their
        # files, so the walk skips them too.
        submodules = submodule_paths(root)
        sources = []
        for current, dirs, files in os.walk(root):
            rel_dir = os.path.relpath(current, root).replace(os.sep, "/")
            dirs[:] = sorted(
                d
                for d in dirs
                if d not in SKIPPED_DIRS
                and posixpath.normpath(posixpath.join(rel_dir, d)) not in submodules
            )
            for name in files:
                if name.endswith(".md"):
                    sources.append(posixpath.normpath(posixpath.join(rel_dir, name)))
        return sorted(sources)

    # ls-files also lists tracked files deleted from the working tree.
    return sorted(
        path
        for path in listed.split("\0")
        if path and os.path.isfile(os.path.join(root, path))
    )


def site_url_from_env(env: Mapping[str, str]) -> str:
    """Return the public URL of the site, ending with `/`.

    `SITE_URL` wins when it is an http(s) URL, else `DEFAULT_SITE_URL`. Every
    build, the local preview included, gets canonical URLs and a sitemap.
    """
    url = env.get("SITE_URL", "")
    if not url.startswith(("https://", "http://")):
        url = DEFAULT_SITE_URL
    return url.rstrip("/") + "/"


def page_url(site_url: str, output_rel: str) -> str:
    """Absolute URL of a page: its directory, without `index.html`."""
    directory = posixpath.dirname(output_rel)
    return site_url + (quote(directory, safe="/") + "/" if directory else "")


def page_description(html_content: str) -> str | None:
    """First paragraph of rendered HTML as plain text, cut for search results.

    Paragraphs without text, such as a row of badges, are skipped. A text
    longer than DESCRIPTION_LENGTH is cut at a word and ends with `...`.
    """
    for paragraph in re.findall(r"<p\b[^>]*>(.*?)</p>", html_content, re.S):
        text = " ".join(_html.unescape(_HTML_TAG_RE.sub("", paragraph)).split())
        if not text:
            continue
        if len(text) > DESCRIPTION_LENGTH:
            text = (
                text[: DESCRIPTION_LENGTH - 3].rsplit(" ", 1)[0].rstrip(",;:") + "..."
            )
        return text
    return None


def seo_head(site: "Site", source: str, title: str, html_content: str) -> str:
    """Description, canonical URL and Open Graph tags of a page's <head>."""
    esc = _html.escape
    description = page_description(html_content)
    tags = []
    if description:
        tags.append(f'<meta name="description" content="{esc(description)}">')
    tags += [
        '<meta property="og:type" content="website">',
        f'<meta property="og:site_name" content="{esc(SITE_TITLE)}">',
        f'<meta property="og:title" content="{esc(title)}">',
    ]
    if description:
        tags.append(f'<meta property="og:description" content="{esc(description)}">')
    card = "summary"
    if site.site_url:
        url = page_url(site.site_url, site.pages[source])
        tags.append(f'<link rel="canonical" href="{esc(url)}">')
        tags.append(f'<meta property="og:url" content="{esc(url)}">')
        if SITE_IMAGE in site.assets:
            image = site.site_url + quote(published_path(SITE_IMAGE), safe="/")
            tags.append(f'<meta property="og:image" content="{esc(image)}">')
            card = "summary_large_image"
    tags.append(f'<meta name="twitter:card" content="{card}">')
    return "\n    ".join(tags)


def sitemap_xml(site: "Site") -> str:
    """sitemaps.org list of every page, home page first."""
    urls = sorted(
        page_url(site.site_url or "", output) for output in site.pages.values()
    )
    entries = "".join(f"  <url><loc>{_html.escape(url)}</loc></url>\n" for url in urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}</urlset>\n"
    )


def repository_url_template(env: Mapping[str, str]) -> str | None:
    """Return a `{kind}`/`{path}` URL template to browse the built commit.

    `kind` is `blob` for files and `tree` for directories. Returns None outside
    GitLab CI and GitHub Actions (e.g. the local post-commit preview).
    """
    if env.get("CI_PROJECT_URL") and env.get("CI_COMMIT_SHA"):
        return f"{env['CI_PROJECT_URL']}/-/{{kind}}/{env['CI_COMMIT_SHA']}/{{path}}"
    if all(
        env.get(k) for k in ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_SHA")
    ):
        return (
            f"{env['GITHUB_SERVER_URL']}/{env['GITHUB_REPOSITORY']}"
            f"/{{kind}}/{env['GITHUB_SHA']}/{{path}}"
        )
    return None


class Site:
    """Pages of one build plus the state needed to resolve links between them."""

    def __init__(
        self, root: str, out_dir: str, sources: list[str], repo_url: str | None
    ) -> None:
        self.root = root
        self.out_dir = out_dir
        self.repo_url = repo_url
        # Public URL of the site, ending with "/" (see site_url_from_env).
        self.site_url: str | None = None
        self.pages = {source: page_output_path(source) for source in sources}
        self.assets: set[str] = set()
        self.missing_links: list[tuple[str, str]] = []
        # (source, url, target source, fragment), checked once every page has
        # been rendered and its ids are known (see check_anchors).
        self.anchor_links: list[tuple[str, str, str, str]] = []

    def rewrite_url(self, url: str, source: str, output_rel: str) -> str:
        """Map a link written for the forge to its location on the site.

        Links to Markdown files go to their page, images are copied into the
        site, and other repository files go to the repository browser (or, for
        a local preview, to the file in the checkout next to public/). A path
        starting with `/` is relative to the repository root, as on the forges.
        """
        if url.startswith("#"):
            self.anchor_links.append((source, url, source, url[1:]))
            return url
        if not url or url.startswith(("?", "//")) or _URL_SCHEME_RE.match(url):
            return url
        rest, has_fragment, fragment = url.partition("#")
        raw_path, has_query, query = rest.partition("?")
        # Query and fragment carry over to the rewritten link unchanged.
        anchor = (f"?{query}" if has_query else "") + (
            f"#{fragment}" if has_fragment else ""
        )
        path = unquote(raw_path)
        base = "" if path.startswith("/") else posixpath.dirname(source)
        target = posixpath.normpath(posixpath.join(base, path.lstrip("/")))
        if target == ".." or target.startswith("../"):
            return url

        cur_dir = posixpath.dirname(output_rel) or "."
        if target in self.pages:
            if has_fragment:
                self.anchor_links.append((source, url, target, fragment))
            return posixpath.relpath(self.pages[target], cur_dir) + anchor

        local = os.path.join(self.root, target)
        if not os.path.exists(local):
            self.missing_links.append((source, url))
            return url
        is_dir = os.path.isdir(local)
        if not is_dir and posixpath.splitext(target)[1].lower() in ASSET_EXTENSIONS:
            self.assets.add(target)
            return posixpath.relpath(published_path(target), cur_dir) + anchor
        if self.repo_url:
            kind = "tree" if is_dir else "blob"
            path_part = "" if target == "." else quote(target)
            return self.repo_url.format(kind=kind, path=path_part) + anchor

        page_dir = os.path.join(self.out_dir, cur_dir)
        return os.path.relpath(local, page_dir).replace(os.sep, "/") + anchor

    def check_anchors(self, anchors: Mapping[str, set[str]]) -> None:
        """Report links to a heading or anchor missing from their target page.

        anchors maps each source to the ids and names of its rendered page.
        """
        for source, url, target, fragment in self.anchor_links:
            if fragment and unquote(fragment) not in anchors.get(target, set()):
                self.missing_links.append((source, url))

    def rewrite_links(self, html: str, source: str, output_rel: str) -> str:
        def attr(match: re.Match[str]) -> str:
            value = match.group(2) if match.group(2) is not None else match.group(3)
            new = self.rewrite_url(_html.unescape(value), source, output_rel)
            return f'{match.group(1)}"{_html.escape(new, quote=True)}"'

        def tag(match: re.Match[str]) -> str:
            return _LINK_ATTR_RE.sub(attr, match.group(0))

        return _LINK_TAG_RE.sub(tag, html)


def page_anchors(html: str) -> set[str]:
    """Return the id and name attributes of the tags of a rendered body.

    Only attributes inside a tag count: `id="x"` written in prose is text.
    """
    return {
        _html.unescape(m.group(1) if m.group(1) is not None else m.group(2))
        for tag in _HTML_OPEN_TAG_RE.findall(html)
        for m in _HTML_ANCHOR_RE.finditer(tag)
    }


def heading_text(html_content: str) -> str | None:
    """Return the text of the first heading of rendered HTML, if any.

    The heading is read from the rendered HTML, so `#` lines inside code
    blocks are ignored and inline Markdown (code, links) is reduced to text.
    """
    match = _HTML_HEADING_RE.search(html_content)
    if match:
        text = _html.unescape(_HTML_TAG_RE.sub("", match.group(1))).strip()
        if text:
            return text
    return None


def page_title(source: str, html_content: str) -> str:
    """Use the site title for the home page, then the first heading, then the path."""
    return title_for(source, heading_text(html_content))


def title_for(source: str, heading: str | None) -> str:
    return SITE_TITLE if source == HOME_SOURCE else heading or source


def render_body(site: Site, source: str) -> tuple[str, str | None]:
    """Render one Markdown source to (HTML body, first heading text)."""
    with open(os.path.join(site.root, source), "r", encoding="utf-8") as f:
        text = f.read()
    output_rel = site.pages[source]

    # Pull fenced code blocks out before any other processing (handles fences
    # nested in list items, which python-markdown mishandles).
    code_blocks: list[str] = []
    text = stash_code_blocks(text, code_blocks)

    # GitLab's [[TOC]] and [[_TOC_]] become the toc extension's [TOC].
    text = _TOC_MARKER_RE.sub("[TOC]", text)

    # Parse alerts (GitLab-style blockquotes); their headings and the page's
    # share one set of ids.
    slugify = HeadingSlugger()
    text = parse_alerts(text, slugify)

    # Convert markdown to html, then fix links before code blocks come back so
    # code samples are never rewritten.
    html_content = site.rewrite_links(
        render_markdown(text, slugify), source, output_rel
    )
    heading = heading_text(html_content)
    return restore_code_blocks(html_content, code_blocks), heading


def render_page(site: Site, source: str, nav: list[NavNode] | None = None) -> str:
    """Render one Markdown source to a complete, minified HTML page.

    nav is the site menu (build_nav_tree); without it, the menu is built from
    the site's pages with their file names as labels.
    """
    html_content, heading = render_body(site, source)
    if nav is None:
        nav = build_nav_tree(site.pages, {})
    return page_document(site, source, html_content, heading, nav)


def page_document(
    site: Site,
    source: str,
    html_content: str,
    heading: str | None,
    nav: list[NavNode],
) -> str:
    """Wrap a rendered body into the site template, with its menu."""
    output_rel = site.pages[source]
    title = title_for(source, heading)
    cur_dir = posixpath.dirname(output_rel) or "."
    css_path = posixpath.relpath(STYLE_FILE, cur_dir)
    ico_path, png_path, apple_path = (
        posixpath.relpath(icon, cur_dir) for icon in SITE_ICONS
    )
    brand_href, nav_items = build_nav(nav, site.pages, source)

    template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_html.escape(title)}</title>
    {seo_head(site, source, title, html_content)}
    <meta name="theme-color" content="#1d2021" media="(prefers-color-scheme: dark)">
    <meta name="theme-color" content="#fbf1c7" media="(prefers-color-scheme: light)">
    <script>{THEME_INIT_JS}</script>
    <link rel="icon" href="{ico_path}" sizes="16x16 32x32 48x48">
    <link rel="icon" href="{png_path}" type="image/png" sizes="192x192">
    <link rel="apple-touch-icon" href="{apple_path}">
    {cdn_tags('.css')}
    <link rel="stylesheet" href="{css_path}">
</head>
<body data-bs-spy="scroll" data-bs-target="#toc">
    <nav class="navbar navbar-expand-md navbar-dark bg-dark sticky-top">
        <div class="container">
            <a class="navbar-brand" href="{brand_href}">{_html.escape(SITE_TITLE)}</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#site-nav" aria-controls="site-nav" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="site-nav">
                <ul class="navbar-nav ms-auto">
                    {nav_items}
                    {theme_menu()}
                </ul>
            </div>
        </div>
    </nav>
    <div class="container py-5">
        <div class="row">
            <div class="col-xl-9 col-lg-8 col-12">
                {html_content}
            </div>
            <div class="col-xl-3 col-lg-4 d-none d-lg-block">
                <nav id="toc" class="sticky-top"></nav>
            </div>
        </div>
    </div>
    {cdn_tags('.js')}
    <script>{THEME_MENU_JS}</script>
    <script>
        $(function() {{
            // Skip the "Table of contents" heading in the bootstrap-toc and hide it
            var tocHeader = $('#table-of-contents');
            if (tocHeader.length) {{
                tocHeader.attr('data-toc-skip', 'true').hide();
                // Also hide any paragraph right after it if it contains the inline TOC marker
                var next = tocHeader.next();
                if (next.length && (next.find('.toc').length || next.hasClass('toc'))) {{
                    next.hide();
                }}
            }}
            // Also hide standard inline TOC
            $('.toc').hide();

            // Initialize bootstrap-toc
            Toc.init({{
                $nav: $('#toc')
            }});
        }});
    </script>
</body>
</html>"""
    return minify_html(template)


def build_site(root: str, out_dir: str, env: Mapping[str, str] | None = None) -> Site:
    """Render every Markdown file of root into out_dir and copy linked assets.

    Files a previous build left in out_dir and this one did not produce are
    removed. Raises ValueError when out_dir contains root.
    """
    sources = discover_markdown(root)
    if HOME_SOURCE not in sources:
        raise FileNotFoundError(f"{HOME_SOURCE} not found in {root}")
    env = os.environ if env is None else env
    site = Site(root, out_dir, sources, repository_url_template(env))
    site.site_url = site_url_from_env(env)

    root_real = os.path.realpath(root)
    out_real = os.path.realpath(out_dir)
    if os.path.commonpath([root_real, out_real]) == out_real:
        raise ValueError(f"output directory {out_dir} contains the sources {root}")
    # Stale files are only removed from a directory this script generated.
    prune = not os.path.exists(out_dir) or os.path.exists(
        os.path.join(out_dir, NOJEKYLL_FILE)
    )

    built = {STYLE_FILE, NOJEKYLL_FILE, *SITE_ICONS}
    # Every body is rendered first: the menu of each page needs every title.
    bodies = {source: render_body(site, source) for source in sources}
    nav = build_nav_tree(sources, {s: heading for s, (_, heading) in bodies.items()})
    anchors = {}
    for source in sources:
        output_rel = site.pages[source]
        output_file = os.path.join(out_dir, output_rel)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        html_content, heading = bodies[source]
        page = page_document(site, source, html_content, heading, nav)
        # The body only: the template's ids and names are not link targets.
        anchors[source] = page_anchors(html_content)
        write_if_changed(output_file, page)
        built.add(output_rel)
    site.check_anchors(anchors)

    for asset in sorted(site.assets):
        asset_rel = published_path(asset)
        dest = os.path.join(out_dir, asset_rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        asset_source = os.path.join(root, asset)
        # Like the pages, an unchanged asset keeps its file and timestamp.
        if not (
            os.path.isfile(dest) and filecmp.cmp(asset_source, dest, shallow=False)
        ):
            shutil.copyfile(asset_source, dest)
        built.add(asset_rel)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    for icon in SITE_ICONS:
        icon_source = os.path.join(script_dir, icon)
        dest = os.path.join(out_dir, icon)
        if not (os.path.isfile(dest) and filecmp.cmp(icon_source, dest, shallow=False)):
            shutil.copyfile(icon_source, dest)

    css_source = os.path.join(script_dir, STYLE_FILE)
    with open(css_source, "r", encoding="utf-8") as src:
        minified_css = minify_css(src.read() + pygments_css())
    write_if_changed(os.path.join(out_dir, STYLE_FILE), minified_css)

    # robots.txt is only read at the root of a host: DEFAULT_SITE_URL is one.
    write_if_changed(os.path.join(out_dir, SITEMAP_FILE), sitemap_xml(site))
    write_if_changed(
        os.path.join(out_dir, ROBOTS_FILE),
        f"User-agent: *\nAllow: /\nSitemap: {site.site_url}{SITEMAP_FILE}\n",
    )
    built.update({SITEMAP_FILE, ROBOTS_FILE})

    # Serve dot-directories (e.g. .gitlab/) verbatim on GitHub Pages (no Jekyll).
    open(os.path.join(out_dir, NOJEKYLL_FILE), "a", encoding="utf-8").close()
    if prune:
        remove_stale_outputs(out_dir, built)
    return site


def remove_stale_outputs(out_dir: str, built: set[str]) -> None:
    """Delete files of out_dir that this build did not produce, then empty dirs.

    The local preview reuses public/, so pages of renamed or deleted Markdown
    files would otherwise stay reachable.
    """
    for current, _dirs, files in os.walk(out_dir, topdown=False):
        rel_dir = os.path.relpath(current, out_dir).replace(os.sep, "/")
        for name in files:
            rel = posixpath.normpath(posixpath.join(rel_dir, name))
            if rel not in built:
                os.remove(os.path.join(current, name))
        if current != out_dir and not os.listdir(current):
            os.rmdir(current)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 gen_pages.py <repository_root> <output_dir>")
        sys.exit(1)

    built = build_site(sys.argv[1], sys.argv[2])
    print(f"gen_pages: {len(built.pages)} pages, {len(built.assets)} assets")
    # A missing target is a broken link on the site: fail the Pages jobs.
    for missing_source, missing_url in built.missing_links:
        print(
            f"gen_pages: {missing_source}: link target not found: {missing_url}",
            file=sys.stderr,
        )
    if built.missing_links:
        sys.exit(1)
