#!/usr/bin/env bash
# Generate the static documentation pages into public/.
# Used by the post-commit hook (see .pre-commit-config.yaml) and reusable in CI.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)" || exit 1

if ! python3 -c 'import markdown' >/dev/null 2>&1; then
    echo "build_pages: python 'markdown' module missing, skipping page generation." >&2
    exit 0
fi

python3 .ci_bin/gen_pages.py README.md             public/index.html                       "Pad's Dotfiles"
python3 .ci_bin/gen_pages.py CHANGELOG.md          public/CHANGELOG.md/index.html          "Changelog"
python3 .ci_bin/gen_pages.py dist/arch/install.md  public/dist/arch/install.md/index.html  "Installation"

echo "build_pages: regenerated public/"
