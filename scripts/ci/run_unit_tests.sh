#!/usr/bin/env sh
# Run the Python unit tests with one process per tests/test_*.py file, JOBS
# at a time (default: CPU count). Most tests drive ansible-playbook and spend
# their time starting Python for each module call, so they parallelize well.
# Used by `make test-python`, `make coverage` and the GitLab unit_tests job.
#
# Usage: run_unit_tests.sh [--coverage]
#   --coverage  record with `coverage run -p` and combine the data files;
#               the caller then runs `coverage report`.
#
# Each file logs to its own file so outputs do not interleave; the logs of
# failing files are printed in full. POSIX sh, for the Alpine CI image.
set -eu

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1

PYTHON=${PYTHON:-python3}
JOBS=${JOBS:-$(nproc 2>/dev/null || echo 2)}
coverage=false
case ${1:-} in
    --coverage) coverage=true ;;
    '') ;;
    *) echo "usage: $0 [--coverage]" >&2; exit 2 ;;
esac

logs=$(mktemp -d)
trap 'rm -rf -- "$logs"' EXIT

if $coverage; then
    "$PYTHON" -m coverage erase
    runner="-m coverage run -p -m unittest"
else
    runner="-m unittest"
fi

files=$(find tests -maxdepth 1 -name 'test_*.py' -exec basename {} \; | sort)
if [ -z "$files" ]; then
    echo "run_unit_tests: no tests/test_*.py file found" >&2
    exit 1
fi

# discover keeps tests/ on sys.path, which the shared test helpers rely on.
# RUNNER is unquoted on purpose: it holds several arguments.
# shellcheck disable=SC2016 # the child sh expands these variables, not this one
printf '%s\n' "$files" |
    LOGS=$logs PYTHON=$PYTHON RUNNER=$runner xargs -P "$JOBS" -I '{}' sh -c '
        "$PYTHON" $RUNNER discover -s tests -p "$1" >"$LOGS/$1.log" 2>&1 \
            || : >"$LOGS/$1.failed"
    ' sh '{}'

failed=0
for marker in "$logs"/*.failed; do
    [ -e "$marker" ] || continue
    name=$(basename "$marker" .failed)
    printf '\n===== FAILED: %s =====\n' "$name" >&2
    cat "$logs/$name.log" >&2
    failed=$((failed + 1))
done

# Same totals as a single unittest run, summed over the files.
cat "$logs"/*.log | awk '
    /^Ran [0-9]+ tests? in/ { tests += $2 }
    /skipped=/ { if (match($0, /skipped=[0-9]+/)) skipped += substr($0, RSTART + 8, RLENGTH - 8) }
    END { printf "Ran %d tests (%d skipped)\n", tests, skipped }
'

if $coverage; then
    "$PYTHON" -m coverage combine -q
fi

if [ "$failed" -gt 0 ]; then
    echo "$failed test file(s) failed" >&2
    exit 1
fi
echo OK
