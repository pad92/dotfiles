#!/usr/bin/env bash
#
# Behavior tests for ~/.bin/claude-statusline: exact rendered lines for real
# git states, absent fields, color thresholds, cost visibility and bad input.

set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
STATUSLINE=${STATUSLINE:-"$ROOT_DIR/ansible/roles/dotfiles/files/home/.bin/claude-statusline"}
TEST_DIR=$(mktemp -d)
trap 'rm -rf -- "$TEST_DIR"' EXIT

export HOME="$TEST_DIR/home"
export GIT_CONFIG_NOSYSTEM=1
export GIT_CONFIG_GLOBAL="$TEST_DIR/gitconfig"
mkdir -p "$HOME"
git config --global user.name test
git config --global user.email test@example.invalid
git config --global init.defaultBranch main

failures=0
fail()
{
    printf 'FAIL: %s\n' "$1" >&2
    failures=$((failures + 1))
}

# expect_output NAME EXPECTED ACTUAL
expect_output()
{
    if [[ $3 != "$2" ]]; then
        fail "$1"
        printf '  expected: %q\n  actual:   %q\n' "$2" "$3" >&2
    fi
}

render() { NO_COLOR=1 "$STATUSLINE"; }
render_color() { env -u NO_COLOR "$STATUSLINE"; }

# A repository whose path contains a space, with one commit pushed, then one
# local commit (ahead 1), two staged files, one modified and one untracked
# file. Distinct counts catch a swap of the index and work-tree columns.
REPO="$HOME/my repo"
git init -q "$REPO"
git init -q --bare "$TEST_DIR/remote.git"
(
    cd "$REPO"
    echo base >tracked
    git add tracked && git commit -qm base
    git remote add origin "$TEST_DIR/remote.git"
    git push -qu origin main
    echo next >>tracked && git commit -qam next
    echo staged >staged && echo staged >staged2 && git add staged staged2
    echo changed >>tracked
    echo new >untracked
)

# Reset times are relative to the real clock, with a 30 s margin against the
# seconds that elapse before the script reads it.
now=$(date +%s)
full_session=$(jq -n --arg dir "$REPO" --argjson now "$now" '{
    model: {display_name: "Opus 5.5"}, effort: {level: "high"},
    workspace: {current_dir: $dir},
    pr: {number: 33, review_state: "approved", kind: "mr"},
    context_window: {used_percentage: 31.7},
    rate_limits: {five_hour: {used_percentage: 23.5, resets_at: ($now + 7230)},
                  seven_day: {used_percentage: 41.2, resets_at: ($now + 4 * 86400 + 30)}},
    cost: {total_cost_usd: 9.99, total_lines_added: 120, total_lines_removed: 30}
}')
expect_output "full session renders on one line" \
    "Opus 5.5 high  ~/my repo [main +2 ~1 ?1 ↑1]  !33 approved  ctx ▰▰▰▱▱▱▱▱▱▱ 31%  23% 2h  41% 4j  +120/-30" \
    "$(render <<<"$full_session")"

# Early in a session most fields are null or absent: nothing may be invented
# (no zero gauge, no git brackets outside a repository, no second line).
mkdir -p "$TEST_DIR/plain"
expect_output "early session outside git shows only what is known" \
    "Sonnet 5.5  $TEST_DIR/plain" \
    "$(render <<<"$(jq -n --arg dir "$TEST_DIR/plain" '{
        model: {display_name: "Sonnet 5.5"}, workspace: {current_dir: $dir},
        context_window: {used_percentage: null, current_usage: null}}')")"
expect_output "empty object renders nothing" "" "$(render <<<'{}')"
expect_output "home directory is abbreviated to a tilde" "~" \
    "$(render <<<"$(jq -n --arg dir "$HOME" '{cwd: $dir}')")"
mkdir -p "${HOME}2"
expect_output "sibling of home sharing its prefix stays absolute" "${HOME}2" \
    "$(render <<<"$(jq -n --arg dir "${HOME}2" '{cwd: $dir}')")"

# Cost is a list-price estimate: only meaningful without subscription limits.
# shellcheck disable=SC2016 # the dollar sign is literal expected output
expect_output "cost shown without rate limits, cents zero-padded" \
    'ctx ▱▱▱▱▱▱▱▱▱▱ 0%  $0.07' \
    "$(render <<<'{"context_window":{"used_percentage":0},"cost":{"total_cost_usd":0.07}}')"
expect_output "cost hidden when subscription limits are present" \
    '10%' \
    "$(render <<<'{"rate_limits":{"five_hour":{"used_percentage":10}},"cost":{"total_cost_usd":3}}')"
expect_output "gateway spend limit is shown as budget" \
    'budget 62%' \
    "$(render <<<'{"rate_limits":{"spend_limit":{"used_percentage":62.8}}}')"

# limit SECONDS_FROM_NOW: render a 7-day window resetting that far ahead.
limit()
{
    render <<<"{\"rate_limits\":{\"seven_day\":{\"used_percentage\":3,
        \"resets_at\":$(($(date +%s) + $1))}}}"
}
expect_output "days are shown from one day left" '3% 1j' "$(limit $((86400 + 30)))"
expect_output "days are rounded down" '3% 6j' "$(limit $((7 * 86400 - 30)))"
expect_output "hours are shown just under one day" '3% 23h' "$(limit $((86400 - 30)))"
expect_output "hours are shown from one hour left" '3% 1h' "$(limit $((3600 + 30)))"
expect_output "minutes are shown just under one hour" '3% 59m' "$(limit $((3600 - 30)))"
expect_output "a reset already past shows no duration" '3%' "$(limit -60)"
expect_output "a missing reset time shows no duration" '3%' \
    "$(render <<<'{"rate_limits":{"seven_day":{"used_percentage":3}}}')"

expect_output "gauge is capped at ten cells" 'ctx ▰▰▰▰▰▰▰▰▰▰ 120%' \
    "$(render <<<'{"context_window":{"used_percentage":120}}')"
expect_output "gauge rounds to the nearest cell" 'ctx ▰▰▰▰▰▱▱▱▱▱ 45%' \
    "$(render <<<'{"context_window":{"used_percentage":45}}')"

# Thresholds: below 50 green, 50 to 79 yellow, 80 and above red.
for case in 49:32 50:33 79:33 80:31; do
    percent=${case%:*} color=$'\e['${case#*:}m
    output=$(render_color <<<"{\"context_window\":{\"used_percentage\":$percent}}")
    [[ $output == *"${color}"▰*" ${percent}%"* || $output == *"${color}"▱*" ${percent}%"* ]] \
        || fail "context at ${percent}% should use color ${case#*:}"
    output=$(render_color <<<"{\"rate_limits\":{\"seven_day\":{\"used_percentage\":$percent}}}")
    [[ $output == *"${color}${percent}%"* ]] \
        || fail "7-day limit at ${percent}% should use color ${case#*:}"
done
[[ $(NO_COLOR=1 "$STATUSLINE" <<<"$full_session") != *$'\e['* ]] \
    || fail "NO_COLOR must remove every escape sequence"

expect_output "GitHub pull request uses #, review state is spelled out" \
    '#7 changes requested' \
    "$(render <<<'{"pr":{"number":7,"review_state":"changes_requested"}}')"
expect_output "optional modes appear only when set" \
    'wt feature-x  INSERT  fast  agent reviewer' \
    "$(render <<<'{"worktree":{"name":"feature-x"},"vim":{"mode":"INSERT"},
        "fast_mode":true,"agent":{"name":"reviewer"}}')"
expect_output "fast mode off and warm cache add nothing" "" \
    "$(render <<<'{"fast_mode":false,"prompt_cache":{"caching_observed":true,"warm":true}}')"
expect_output "cold cache is flagged once caching was observed" 'cache froid' \
    "$(render <<<'{"prompt_cache":{"caching_observed":true,"warm":false}}')"
expect_output "no cache warning when caching was never observed" "" \
    "$(render <<<'{"prompt_cache":{"caching_observed":false,"warm":false}}')"

# Detached HEAD shows the abbreviated commit instead of "(detached)".
DETACHED="$TEST_DIR/detached"
git clone -q "$TEST_DIR/remote.git" "$DETACHED"
git -C "$DETACHED" checkout -q --detach
oid=$(git -C "$DETACHED" rev-parse --short=7 HEAD)
expect_output "detached head shows the short commit" "$DETACHED [$oid]" \
    "$(render <<<"$(jq -n --arg dir "$DETACHED" '{cwd: $dir}')")"

# Unmerged paths are counted separately from staged/modified files.
CONFLICT="$TEST_DIR/conflict"
git clone -q "$TEST_DIR/remote.git" "$CONFLICT"
(
    cd "$CONFLICT"
    git switch -qc other
    echo theirs >tracked && git commit -qam theirs
    git switch -q main
    echo ours >tracked && git commit -qam ours
    git merge -q other >/dev/null 2>&1 || true
)
expect_output "merge conflict is counted, ahead and behind tracked" \
    "$CONFLICT [main ≠1 ↑1]" \
    "$(render <<<"$(jq -n --arg dir "$CONFLICT" '{cwd: $dir}')")"

expect_output "invalid JSON is reported in the bar, not hidden" \
    'claude-statusline: invalid session JSON' "$(render <<<'not json')"
render <<<'not json' >/dev/null || fail "invalid JSON must exit 0 to stay visible"

if ((failures)); then
    printf '%d claude-statusline test(s) failed\n' "$failures" >&2
    exit 1
fi
printf 'claude-statusline: all tests passed\n'
