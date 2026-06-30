#!/usr/bin/env sh
# Print a single version's release notes from CHANGELOG.md to stdout.
# Shared by the GitHub (release.yml) and GitLab (create_release) release jobs.
# Usage: extract_release_notes.sh <version-tag>   e.g. v5.4.0
#
# POSIX sh only (the GitLab release-cli image is busybox-based, no bash).
set -eu

VERSION="${1:?usage: extract_release_notes.sh <version-tag>}"

# Grab the block from the "## ... [VERSION]" header to the next H2 header.
# Match the version literally with index(), so tag names never become regex.
notes="$(awk -v version="$VERSION" '
    /^##[[:space:]]/ {
        if (in_section) {
            exit
        }
        if (index($0, "[" version "]") > 0) {
            in_section = 1
            next
        }
    }
    in_section {
        print
    }
' CHANGELOG.md)"

# Fall back to a placeholder when the section is empty or whitespace-only.
if [ -z "$(printf '%s' "$notes" | tr -d '[:space:]')" ]; then
    notes="No specific notes found in CHANGELOG.md for $VERSION."
fi

printf '%s\n' "$notes"
