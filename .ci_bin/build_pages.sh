#!/usr/bin/env sh
# Generate the static documentation pages into public/.
# Used by the post-commit hook (see .pre-commit-config.yaml) and reusable in CI.
# POSIX sh only, so it runs on minimal CI images (e.g. the GitLab alpine job).
set -eu

# Run from the repo root. Prefer git, but fall back to the current directory
# for CI images without git installed (e.g. the GitLab alpine pages job).
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1

if ! python3 -c 'import markdown' >/dev/null 2>&1; then
    echo "build_pages: python 'markdown' module missing, skipping page generation." >&2
    exit 0
fi

# Output paths mirror each source path under public/.
python3 .ci_bin/gen_pages.py README.md                    public/index.html                              "Pad's Dotfiles"
python3 .ci_bin/gen_pages.py CHANGELOG.md                 public/CHANGELOG.md/index.html                 "Changelog"
python3 .ci_bin/gen_pages.py dist/arch/install.md         public/dist/arch/install.md/index.html         "Installation"
# Publish under github/ (no leading dot): actions/upload-pages-artifact strips
# .git and .github from the deployed tarball, which would 404 the page.
python3 .ci_bin/gen_pages.py .github/workflows/README.md  public/github/workflows/README.md/index.html  "CI Workflows"
python3 .ci_bin/gen_pages.py .gitlab/README.md            public/.gitlab/README.md/index.html            "GitLab CI"

# Copy static assets referenced by the rendered docs into public/, mirroring
# their source path so relative links (e.g. the README showcase image) resolve
# correctly on both GitHub Pages and GitLab Pages.
for asset in dist/hyprland.webp; do
    if [ -f "$asset" ]; then
        mkdir -p "public/$(dirname "$asset")"
        cp "$asset" "public/$asset"
    fi
done

# Serve dot-directories (e.g. .github/) verbatim on GitHub Pages (no Jekyll).
touch public/.nojekyll

echo "build_pages: regenerated public/"
