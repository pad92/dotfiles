import sys
import os
import re
import markdown
import shutil

def get_alert_resources(alert_type):
    # SVG icons from Octicons/Pajamas
    icons = {
        'NOTE': (
            '<svg class="octicon octicon-info" viewBox="0 0 16 16" version="1.1" width="16" height="16" aria-hidden="true">'
            '<path d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8Zm8-3a1 1 0 1 0 0-2 1 1 0 0 0 0 2Zm3 3H8.75v3.25a.25.25 0 0 0 .25.25h1a.75.75 0 0 1 0 1.5h-3a.75.75 0 0 1 0-1.5h1V6.75A.75.75 0 0 1 7.75 6H11a.75.75 0 0 1 0 1.5Z"></path>'
            '</svg>',
            'Note'
        ),
        'TIP': (
            '<svg class="octicon octicon-light-bulb" viewBox="0 0 16 16" version="1.1" width="16" height="16" aria-hidden="true">'
            '<path d="M8 1.5c-2.363 0-4 1.637-4 4 0 .918.353 1.703.844 2.5a.75.75 0 0 1 .156.467v1.283c0 .338.224.626.549.724l.325.097a.75.75 0 0 1 .526.718v.5a.75.75 0 0 1-.75.75H5a.75.75 0 0 1 0-1.5h.25v-.31L4.85 10.9A2.25 2.25 0 0 1 3.5 8.813V7.218A4.25 4.25 0 0 1 7.25 3h1.5A4.25 4.25 0 0 1 13 7.218v1.595a2.25 2.25 0 0 1-1.35 2.087l-.4 1.205V12.4H11a.75.75 0 0 1 0 1.5h-.25a.75.75 0 0 1-.75-.75v-.5a.75.75 0 0 1 .526-.718l.325-.097a.75.75 0 0 1 .549-.724V8.467a.75.75 0 0 1 .156-.467c.49-.797.843-1.582.843-2.5 0-2.363-1.637-4-4-4ZM5.496 7.42a5.75 5.75 0 0 0-.746-1.92c-.143-.23-.25-.49-.25-.75 0-1.363.937-2.5 2.5-2.5h1.5c1.563 0 2.5 1.137 2.5 2.5 0 .26-.107.52-.25.75-.245.395-.5.852-.746 1.92l-.153.667H6.649l-.153-.667ZM9 15.25a1.25 1.25 0 1 1-2.5 0h2.5Z"></path>'
            '</svg>',
            'Tip'
        ),
        'IMPORTANT': (
            '<svg class="octicon octicon-report" viewBox="0 0 16 16" version="1.1" width="16" height="16" aria-hidden="true">'
            '<path d="M0 1.75C0 .783.783 0 1.75 0h12.5C15.217 0 16 .783 16 1.75v12.5A1.75 1.75 0 0 1 14.25 16H1.75A1.75 1.75 0 0 1 0 14.25ZM1.75-.25a.25.25 0 0 0-.25.25v12.5c0 .138.112.25.25.25h12.5a.25.25 0 0 0 .25-.25V1.75a.25.25 0 0 0-.25-.25ZM8 3.25a.75.75 0 0 1 .75.75v3.25a.75.75 0 0 1-1.5 0V4a.75.75 0 0 1 .75-.75Zm0 7a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z"></path>'
            '</svg>',
            'Important'
        ),
        'WARNING': (
            '<svg class="octicon octicon-alert" viewBox="0 0 16 16" version="1.1" width="16" height="16" aria-hidden="true">'
            '<path d="M6.457 1.047c.66-1.1 2.227-1.1 2.887 0l6.03 10.05c.66 1.1-.124 2.5-1.444 2.5H1.87c-1.32 0-2.104-1.4-1.444-2.5Zm2.127.854a.75.75 0 0 0-1.168 0L1.386 11.95a.75.75 0 0 0 .643 1.135h12.042a.75.75 0 0 0 .643-1.135Zm-1.834 8.6a1 1 0 1 1 2 0 1 1 0 0 1-2 0Zm1.25-4.75a.75.75 0 0 0-1.5 0v2.5a.75.75 0 0 0 1.5 0Z"></path>'
            '</svg>',
            'Warning'
        ),
        'CAUTION': (
            '<svg class="octicon octicon-stop" viewBox="0 0 16 16" version="1.1" width="16" height="16" aria-hidden="true">'
            '<path d="M4.47.22A.75.75 0 0 1 5 0h6c.2 0 .39.08.53.22l4.25 4.25c.14.14.22.33.22.53v6c0 .2-.08.39-.22.53l-4.25 4.25A.75.75 0 0 1 11 16H5a.75.75 0 0 1-.53-.22L.22 11.53A.75.75 0 0 1 0 11V5c0-.2.08-.39.22-.53Zm.8 1.28L1.5 5.25v5.5l3.77 3.77h5.46l3.77-3.77v-5.5L10.73 1.5Z"></path><path d="M8 4a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 8 4Zm0 7a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z"></path>'
            '</svg>',
            'Caution'
        )
    }
    return icons.get(alert_type, (None, alert_type))

def parse_alerts(text):
    lines = text.split('\n')
    new_lines = []
    i = 0
    n = len(lines)
    
    while i < n:
        line = lines[i]
        match = re.match(r'^(\s*)>\s*\[!(TIP|NOTE|WARNING|IMPORTANT|CAUTION)\](?:\s*(.*))?$', line, re.IGNORECASE)
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
                next_match = re.match(r'^\s*>\s?(.*)$', next_line)
                if next_match:
                    alert_lines.append(next_match.group(1))
                    i += 1
                else:
                    break
            
            alert_content = '\n'.join(alert_lines)
            compiled_content = markdown.markdown(alert_content, extensions=['extra', 'codehilite', 'toc'])
            
            icon_svg, title_text = get_alert_resources(alert_type)
            
            alert_html = (
                f'<div class="markdown-alert markdown-alert-{alert_type.lower()}">\n'
                f'<p class="markdown-alert-title">{icon_svg}{title_text}</p>\n'
                f'{compiled_content}\n'
                f'</div>'
            )
            
            indented_lines = []
            for l in alert_html.split('\n'):
                if l.strip():
                    indented_lines.append(indent + l)
                else:
                    indented_lines.append(l)
            alert_html = '\n'.join(indented_lines)
            
            new_lines.append(alert_html)
        else:
            new_lines.append(line)
            i += 1
            
    return '\n'.join(new_lines)

def generate_html(input_file, output_file, title):
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()

    # Replace [[TOC]] and [[_TOC_]] with [TOC] so python-markdown's toc extension recognizes them
    text = text.replace('[[TOC]]', '[TOC]').replace('[[_TOC_]]', '[TOC]')

    # Parse alerts (GitLab-style blockquotes)
    text = parse_alerts(text)

    # Convert markdown to html
    html_content = markdown.markdown(text, extensions=['extra', 'codehilite', 'toc'])

    # Determine CSS path relative to the output file
    # The output files are in public/index.html, public/CHANGELOG.md/index.html, etc.
    # We want to link to public/style.css
    # For index.html: style.css
    # For CHANGELOG.md/index.html: ../style.css
    # For dist/arch/install.md/index.html: ../../../style.css

    # We'll just use a relative path based on the output directory depth
    depth = output_file.count('/')
    css_path = "../" * (depth - 1) + "style.css" if depth > 1 else "style.css"
    if output_file.startswith("public/") and depth == 1: # public/index.html
        css_path = "style.css"
    elif output_file.startswith("public/") and depth > 1:
        # public/CHANGELOG.md/index.html -> depth 2 -> ../style.css
        # public/dist/arch/install.md/index.html -> depth 4 -> ../../../style.css
        # The number of ../ is depth - 1
        css_path = "../" * (depth - 1) + "style.css"

    # Copy style.css to the target directory automatically
    script_dir = os.path.dirname(os.path.abspath(__file__))
    css_source = os.path.join(script_dir, "style.css")
    
    if os.path.exists(css_source):
        css_dest = os.path.normpath(os.path.join(os.path.dirname(output_file), css_path))
        css_dest_dir = os.path.dirname(css_dest)
        if css_dest_dir:
            os.makedirs(css_dest_dir, exist_ok=True)
        shutil.copy2(css_source, css_dest)

    template = f'''<!DOCTYPE html>
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
</html>'''

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(template)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 gen_pages.py <input_file> <output_file> <title>")
        sys.exit(1)

    generate_html(sys.argv[1], sys.argv[2], sys.argv[3])
