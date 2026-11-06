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

# Every Markdown file becomes a page whose path mirrors its source path, and
# relative links are rewritten for the site (see gen_pages.py). Linked images
# are copied into public/; other linked files point to the repository browser
# in GitLab CI and GitHub Actions.
python3 scripts/ci/gen_pages.py . public

echo "build_pages: regenerated public/"
