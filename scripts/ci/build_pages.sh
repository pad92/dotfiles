#!/usr/bin/env sh
# Generate the static documentation pages into public/.
# Used by the post-commit hook (see .pre-commit-config.yaml) and reusable in CI.
# POSIX sh only, so it runs on minimal CI images (e.g. the GitLab alpine job).
set -eu

# Run from the repo root. Prefer git, but fall back to the current directory
# for CI images without git installed (e.g. the GitLab alpine pages job).
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1

# The local post-commit hook skips quietly; a CI job (GitLab and GitHub both
# set CI) fails here instead of later on a missing public/ artifact.
if ! python3 -c 'import markdown' >/dev/null 2>&1; then
    if [ -n "${CI:-}" ]; then
        echo "build_pages: python 'markdown' module missing, cannot build the site." >&2
        exit 1
    fi
    echo "build_pages: python 'markdown' module missing, skipping page generation." >&2
    exit 0
fi
if ! python3 -c 'import pygments' >/dev/null 2>&1; then
    echo "build_pages: python 'pygments' module missing, code blocks are not highlighted." >&2
fi

# Every Markdown file becomes a page whose path mirrors its source path, and
# relative links are rewritten for the site (see gen_pages.py). Linked images
# are copied into public/; other linked files point to the repository browser
# in GitLab CI and GitHub Actions.
python3 scripts/ci/gen_pages.py . public

echo "build_pages: regenerated public/"
