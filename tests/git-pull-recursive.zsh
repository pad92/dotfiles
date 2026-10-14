#!/usr/bin/env zsh

set -euo pipefail
ROOT_DIR=${0:A:h:h}
TEST_DIR=$(mktemp -d)
trap 'rm -rf -- "$TEST_DIR"' EXIT
mkdir -p "$TEST_DIR/one/.git" "$TEST_DIR/two/.git"
source "$ROOT_DIR/zsh/functions/git.zsh"

git() {
  print -r -- "$*" >> "$TEST_DIR/git-calls"
  return 1
}

cd "$TEST_DIR"
if git_pull_r; then
  print -u2 'FAIL: git_pull_r hid repository pull failures'
  exit 1
fi
[[ $(wc -l < "$TEST_DIR/git-calls") -eq 2 ]] \
  || { print -u2 'FAIL: not every repository was attempted'; exit 1; }
if grep -q 'checkout' "$TEST_DIR/git-calls"; then
  print -u2 'FAIL: git_pull_r changed a repository branch after a pull failure'
  exit 1
fi
if ! grep -q -- '--ff-only' "$TEST_DIR/git-calls"; then
  print -u2 'FAIL: git_pull_r did not require fast-forward updates'
  exit 1
fi
print 'PASS: recursive git pull preserves branches and reports failures'
