#!/usr/bin/env sh
# Print a single version's release notes from CHANGELOG.md to stdout.
# Shared by the GitHub (release.yml) and GitLab (create_release) release jobs.
# Usage: extract_release_notes.sh <version-tag>   e.g. v5.4.0
#
# POSIX sh only (the GitLab release-cli image is busybox-based, no bash).
set -eu

VERSION="${1:?usage: extract_release_notes.sh <version-tag>}"

# Grab the block from the "## [VERSION]" header to the next "## [" header,
# then drop the header line (first) and the next-version boundary line (last).
notes="$(sed -n "/## \[$VERSION\]/,/## \[/p" CHANGELOG.md | sed '1d;$d')"

# Fall back to a placeholder when the section is empty or whitespace-only.
if [ -z "$(printf '%s' "$notes" | tr -d '[:space:]')" ]; then
    notes="No specific notes found in CHANGELOG.md for $VERSION."
fi

printf '%s\n' "$notes"
