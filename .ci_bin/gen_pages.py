import sys
import os
import re
import html as _html
import posixpath
import markdown

try:
    from pygments import highlight as _pyg_highlight
    from pygments.formatters import HtmlFormatter as _PygHtmlFormatter
    from pygments.lexers import get_lexer_by_name as _pyg_lexer
    from pygments.util import ClassNotFound as _PygClassNotFound

    _HAVE_PYGMENTS = True
except Exception:  # pragma: no cover - pygments is optional
    _HAVE_PYGMENTS = False

# Site navigation menu: (label, target page relative to the public/ root).
# Links are resolved relative to each page so the site works under a subpath
# (e.g. project GitHub/GitLab Pages served from /<repo>/).
SITE_NAV = [
    ("Home", "index.html"),
    ("Changelog", "CHANGELOG.md/index.html"),
    ("Installation", "dist/arch/install.md/index.html"),
    # Published under github/ (not .github/): actions/upload-pages-artifact
    # excludes .git and .github from the deployed tarball (would 404 otherwise).
    ("CI Workflows", "github/workflows/README.md/index.html"),
    ("GitLab CI", ".gitlab/README.md/index.html"),
]


# Emoji / pictographic symbol ranges plus variation selectors and ZWJ.
EMOJI_RE = re.compile(
    "["
    "\U0001f000-\U0001faff"  # symbols, emoticons, transport, supplemental, etc.
    "\U00002600-\U000027bf"  # misc symbols & dingbats
    "\U00002b00-\U00002bff"  # misc symbols and arrows
    "\U00002300-\U000023ff"  # misc technical (e.g. ⌨ keyboard, ⏰ clock)
    "\U00002190-\U000021ff"  # arrows
    "️‍"  # variation selector-16 and zero-width joiner
    "]+"
)


def strip_heading_icons(text):
    """Remove emoji/icons from Markdown headings (outside fenced code blocks)."""
    lines = text.split("\n")
    in_code = False
    for i, line in enumerate(lines):
        if re.match(r"^\s*```", line):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = re.match(r"^(\s*#{1,6}\s+)(.*)$", line)
        if m:
            content = re.sub(r"\s{2,}", " ", EMOJI_RE.sub("", m.group(2))).strip()
            lines[i] = m.group(1) + content
    return "\n".join(lines)


def build_nav(output_file):
    """Return (brand_href, nav_items_html) with links relative to output_file."""
    # Drop the leading 'public/' segment to get the path relative to the site root.
    root_rel = "/".join(output_file.replace(os.sep, "/").split("/")[1:])
    cur_dir = posixpath.dirname(root_rel) or "."

    items = []
    for label, target in SITE_NAV:
        href = posixpath.relpath(target, cur_dir)
        if target == root_rel:
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

            alert_content = preprocess_markdown("\n".join(alert_lines))
            compiled_content = markdown.markdown(
                alert_content, extensions=["extra", "codehilite", "toc"]
            )

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


def generate_html(input_file, output_file, title):
    with open(input_file, "r", encoding="utf-8") as f:
        text = f.read()

    # Pull fenced code blocks out before any other processing (handles fences
    # nested in list items, which python-markdown mishandles).
    code_blocks = []
    text = stash_code_blocks(text, code_blocks)

    # Strip emoji/icons from headings (kept in the source for the repo view).
    text = strip_heading_icons(text)

    # Replace [[TOC]] and [[_TOC_]] with [TOC] so python-markdown's toc extension recognizes them
    text = text.replace("[[TOC]]", "[TOC]").replace("[[_TOC_]]", "[TOC]")

    # Parse alerts (GitLab-style blockquotes)
    text = parse_alerts(text)

    # Convert markdown to html
    html_content = markdown.markdown(
        preprocess_markdown(text), extensions=["extra", "codehilite", "toc"]
    )

    # Reinsert the rendered code blocks, dropping any <p> wrapper Markdown added.
    for i, block in enumerate(code_blocks):
        token = f"xxcodeblock{i}xx"
        html_content = html_content.replace(f"<p>{token}</p>", block).replace(
            token, block
        )

    # CSS lives at the public/ root; link to it with a relative path based on
    # how deep the output file sits (e.g. public/index.html -> style.css,
    # public/CHANGELOG.md/index.html -> ../style.css,
    # public/dist/arch/install.md/index.html -> ../../../style.css).
    depth = output_file.count("/")
    css_path = "../" * (depth - 1) + "style.css" if depth > 1 else "style.css"

    # Copy style.css to the target directory automatically
    script_dir = os.path.dirname(os.path.abspath(__file__))
    css_source = os.path.join(script_dir, "style.css")

    if os.path.exists(css_source):
        css_dest = os.path.normpath(
            os.path.join(os.path.dirname(output_file), css_path)
        )
        css_dest_dir = os.path.dirname(css_dest)
        if css_dest_dir:
            os.makedirs(css_dest_dir, exist_ok=True)
        with open(css_source, "r", encoding="utf-8") as src:
            minified_css = minify_css(src.read() + pygments_css())
        with open(css_dest, "w", encoding="utf-8") as dst:
            dst.write(minified_css)

    brand_href, nav_items = build_nav(output_file)

    template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/afeld/bootstrap-toc@v1.0.1/dist/bootstrap-toc.min.css">
    <link rel="stylesheet" href="{css_path}">
</head>
<body data-bs-spy="scroll" data-bs-target="#toc">
    <nav class="navbar navbar-expand-md navbar-dark bg-dark sticky-top">
        <div class="container">
            <a class="navbar-brand" href="{brand_href}">Pad's Dotfiles</a>
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

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(minify_html(template))


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 gen_pages.py <input_file> <output_file> <title>")
        sys.exit(1)

    generate_html(sys.argv[1], sys.argv[2], sys.argv[3])
