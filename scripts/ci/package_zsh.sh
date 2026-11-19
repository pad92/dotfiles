#!/usr/bin/env sh
# Package the Zsh tree, a .zshrc rendered without Jinja and the plugins pinned
# in the dotfiles role, without their .git directory, as the archive named by
# the first argument.
# Shared by the GitLab package_zsh job and the GitHub package-zsh.yml workflow.
# Needs git, tar and PyYAML. POSIX sh only, so it runs on minimal CI images.
set -eu

archive=${1:?usage: package_zsh.sh ARCHIVE}

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
mkdir package
python3 scripts/ci/build_zsh_package.py package
tar -czf "$archive" -C package .zshenv .zshrc .local
