#!/usr/bin/env sh
# Package the Vim configuration and the plugins pinned in the dotfiles role,
# without their .git directory, as the archive named by the first argument.
# Shared by the GitLab package_vim job and the GitHub package-vim.yml workflow.
# Needs git, tar and PyYAML. POSIX sh only, so it runs on minimal CI images.
set -eu

archive=${1:?usage: package_vim.sh ARCHIVE}
home=ansible/roles/dotfiles/files/home

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
mkdir package
cp -a "$home/.vim" "$home/.vimrc" package/
python3 scripts/ci/fetch_vim_plugins.py package
tar -czf "$archive" -C package .vim .vimrc
