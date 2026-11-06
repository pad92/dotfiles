import html as _html
import os
import posixpath
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping
from urllib.parse import quote, unquote

import markdown

try:
    from pygments import highlight as _pyg_highlight
    from pygments.formatters import HtmlFormatter as _PygHtmlFormatter
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

# Site navigation menu: (label, source Markdown file).
SITE_NAV = [
    ("Home", HOME_SOURCE),
    ("Ansible", "ansible/README.md"),
    ("Installation", "dist/arch/install.md"),
    ("Changelog", "CHANGELOG.md"),
    ("CI Workflows", ".github/workflows/README.md"),
    ("GitLab CI", ".gitlab/README.md"),
]
SITE_TITLE = "Pad's Dotfiles"

_URL_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_LINK_ATTR_RE = re.compile(r'\b(href|src)="([^"]*)"')
_HEADING_RE = re.compile(r"^#{1,6}[ \t]+(.+?)[ \t#]*$", re.MULTILINE)


def page_output_path(source: str) -> str:
    """Return the page path, relative to the site root, for a Markdown source."""
    if source == HOME_SOURCE:
        return "index.html"
    for prefix, replacement in RENAMED_PREFIXES.items():
        if source.startswith(prefix):
            source = replacement + source[len(prefix) :]
            break
    return f"{source}/index.html"


def build_nav(output_rel: str) -> tuple[str, str]:
    """Return (brand_href, nav_items_html) with links relative to output_rel.

    Relative links keep the site working under a subpath (e.g. project
    GitHub/GitLab Pages served from /<repo>/).
    """
    cur_dir = posixpath.dirname(output_rel) or "."

    items = []
    for label, source in SITE_NAV:
        target = page_output_path(source)
        href = posixpath.relpath(target, cur_dir)
        if target == output_rel:
            items.append(
                f'<li class="nav-item"><a class="nav-link active" '
                f'aria-current="page" href="{href}">{label}</a></li>'
            )
        else:
            items.append(
                f'<li class="nav-item"><a class="nav-link" href="{href}">{label}</a></li>'
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
    """Collapse whitespace in HTML while preserving blocks where whitespace is
    significant (code, scripts, inline styles)."""
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
    html = re.sub(r">\s+<", "><", html)
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


def pygments_css():
    """Syntax-highlighting colours for `.codehilite`, themed for the dark pages.

    Returns an empty string when Pygments is unavailable (code still renders,
    just without colours). The code box background is left to the themed `pre`
    rule, so only the token colours come from the Pygments style.
    """
    if not _HAVE_PYGMENTS:
        return ""
    defs = _PygHtmlFormatter(style="dracula").get_style_defs(".codehilite")
    return "\n" + defs + "\n.codehilite{background:transparent}\n"


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


def stash_code_blocks(text, store):
    """Replace fenced code blocks with placeholders and render them ourselves.

    python-markdown's `fenced_code` does not recognise fences nested inside list
    items (it turns them into inline code), so we extract every fenced block
    here — dedenting by the opening fence's indentation — render it, and reinsert
    the HTML after Markdown conversion. The placeholder keeps the fence's indent
    so it stays within its list item.
    """
    pattern = re.compile(
        r"^([ \t]*)```([\w+-]*)[ \t]*\n(.*?)\n[ \t]*```[ \t]*$",
        re.MULTILINE | re.DOTALL,
    )

    def repl(match):
        indent, lang, body = match.group(1), match.group(2), match.group(3)
        n = len(indent)
        code = "\n".join(
            line[n:] if line[:n].strip() == "" else line for line in body.split("\n")
        )
        token = f"xxcodeblock{len(store)}xx"
        store.append(render_code_block(code, lang))
        return indent + token

    return pattern.sub(repl, text)


def preprocess_markdown(text):
    # Regex to find fenced code blocks that may be indented (e.g. inside list items)
    pattern = re.compile(
        r"^(\s*)```([a-zA-Z0-9_+-]+)[ \t]*\n(.*?)\n\1```[ \t]*$",
        re.MULTILINE | re.DOTALL,
    )

    def replace_fenced_code(match):
        indent = match.group(1)
        lang = match.group(2)
        code = match.group(3)

        if not indent:
            return match.group(0)

        lines = code.split("\n")
        # Prepend 4 extra spaces of indentation to make it a standard indented code block
        indented_lines = ["    " + line for line in lines]
        # Prepend 4 spaces of indentation and ::: to specify the language for codehilite
        header = indent + "    " + f":::{lang}"
        return f"\n{header}\n" + "\n".join(indented_lines) + "\n"

    return pattern.sub(replace_fenced_code, text)


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


def render_markdown(text):
    """Render Markdown using the compact nested-list style used by the docs."""
    text = normalize_nested_list_indentation(preprocess_markdown(text))
    return markdown.markdown(text, extensions=["extra", "codehilite", "toc"])


def parse_alerts(text):
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

            compiled_content = render_markdown("\n".join(alert_lines))

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
        self.pages = {source: page_output_path(source) for source in sources}
        self.assets: set[str] = set()
        self.missing_links: list[tuple[str, str]] = []

    def rewrite_url(self, url: str, source: str, output_rel: str) -> str:
        """Map a link written for the forge to its location on the site.

        Links to Markdown files go to their page, images are copied into the
        site, and other repository files go to the repository browser (or, for
        a local preview, to the file in the checkout next to public/).
        """
        if not url or url.startswith(("#", "/")) or _URL_SCHEME_RE.match(url):
            return url
        raw_path, has_fragment, fragment = url.partition("#")
        anchor = f"#{fragment}" if has_fragment else ""
        path = unquote(raw_path)
        target = posixpath.normpath(posixpath.join(posixpath.dirname(source), path))
        if target == ".." or target.startswith("../"):
            return url

        cur_dir = posixpath.dirname(output_rel) or "."
        if target in self.pages:
            return posixpath.relpath(self.pages[target], cur_dir) + anchor

        local = os.path.join(self.root, target)
        if not os.path.exists(local):
            self.missing_links.append((source, url))
            return url
        is_dir = os.path.isdir(local)
        if not is_dir and posixpath.splitext(target)[1].lower() in ASSET_EXTENSIONS:
            self.assets.add(target)
            return posixpath.relpath(target, cur_dir) + anchor
        if self.repo_url:
            kind = "tree" if is_dir else "blob"
            path_part = "" if target == "." else quote(target)
            return self.repo_url.format(kind=kind, path=path_part) + anchor

        page_dir = os.path.join(self.out_dir, cur_dir)
        return os.path.relpath(local, page_dir).replace(os.sep, "/") + anchor

    def rewrite_links(self, html: str, source: str, output_rel: str) -> str:
        def repl(match: re.Match[str]) -> str:
            url = _html.unescape(match.group(2))
            new = self.rewrite_url(url, source, output_rel)
            return f'{match.group(1)}="{_html.escape(new, quote=True)}"'

        return _LINK_ATTR_RE.sub(repl, html)


def page_title(source: str, text: str) -> str:
    """Use the navigation label, then the first heading, then the source path."""
    for label, nav_source in SITE_NAV:
        if nav_source == source:
            return SITE_TITLE if source == HOME_SOURCE else label
    match = _HEADING_RE.search(text)
    return match.group(1) if match else source


def render_page(site: Site, source: str) -> str:
    """Render one Markdown source to a complete, minified HTML page."""
    with open(os.path.join(site.root, source), "r", encoding="utf-8") as f:
        text = f.read()
    output_rel = site.pages[source]
    title = page_title(source, text)

    # Pull fenced code blocks out before any other processing (handles fences
    # nested in list items, which python-markdown mishandles).
    code_blocks = []
    text = stash_code_blocks(text, code_blocks)

    # Replace [[TOC]] and [[_TOC_]] with [TOC] so python-markdown's toc extension recognizes them
    text = text.replace("[[TOC]]", "[TOC]").replace("[[_TOC_]]", "[TOC]")

    # Parse alerts (GitLab-style blockquotes)
    text = parse_alerts(text)

    # Convert markdown to html, then fix links before code blocks come back so
    # code samples are never rewritten.
    html_content = site.rewrite_links(render_markdown(text), source, output_rel)

    # Reinsert the rendered code blocks, dropping any <p> wrapper Markdown added.
    for i, block in enumerate(code_blocks):
        token = f"xxcodeblock{i}xx"
        html_content = html_content.replace(f"<p>{token}</p>", block).replace(
            token, block
        )

    cur_dir = posixpath.dirname(output_rel) or "."
    css_path = posixpath.relpath(STYLE_FILE, cur_dir)
    brand_href, nav_items = build_nav(output_rel)

    template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_html.escape(title)}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/afeld/bootstrap-toc@v1.0.1/dist/bootstrap-toc.min.css">
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
    <script src="https://code.jquery.com/jquery-3.7.1.slim.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/gh/afeld/bootstrap-toc@v1.0.1/dist/bootstrap-toc.min.js"></script>
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
    """Render every Markdown file of root into out_dir and copy linked assets."""
    sources = discover_markdown(root)
    if HOME_SOURCE not in sources:
        raise FileNotFoundError(f"{HOME_SOURCE} not found in {root}")
    site = Site(
        root,
        out_dir,
        sources,
        repository_url_template(os.environ if env is None else env),
    )

    for source in sources:
        output_file = os.path.join(out_dir, site.pages[source])
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        write_if_changed(output_file, render_page(site, source))

    for asset in sorted(site.assets):
        dest = os.path.join(out_dir, asset)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(os.path.join(root, asset), dest)

    css_source = os.path.join(os.path.dirname(os.path.abspath(__file__)), STYLE_FILE)
    with open(css_source, "r", encoding="utf-8") as src:
        minified_css = minify_css(src.read() + pygments_css())
    write_if_changed(os.path.join(out_dir, STYLE_FILE), minified_css)

    # Serve dot-directories (e.g. .gitlab/) verbatim on GitHub Pages (no Jekyll).
    open(os.path.join(out_dir, ".nojekyll"), "a", encoding="utf-8").close()
    return site


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 gen_pages.py <repository_root> <output_dir>")
        sys.exit(1)

    built = build_site(sys.argv[1], sys.argv[2])
    for missing_source, missing_url in built.missing_links:
        print(
            f"gen_pages: {missing_source}: link target not found: {missing_url}",
            file=sys.stderr,
        )
    print(f"gen_pages: {len(built.pages)} pages, {len(built.assets)} assets")
