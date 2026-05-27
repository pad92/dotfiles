import sys
import os
import markdown
import shutil

def generate_html(input_file, output_file, title):
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()

    # Replace [[TOC]] and [[_TOC_]] with [TOC] so python-markdown's toc extension recognizes them
    text = text.replace('[[TOC]]', '[TOC]').replace('[[_TOC_]]', '[TOC]')

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
