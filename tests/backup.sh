#!/usr/bin/env bash
#
# Integration tests of backup.sh. ssh, rsync, ssh-add, hostnamectl, id and the
# package managers are fakes on PATH, so nothing touches the network or the
# NAS.

set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
BACKUP=${BACKUP:-"$ROOT_DIR/ansible/roles/dotfiles/files/home/.bin/backup.sh"}
TEST_DIR=$(cd -- "$(mktemp -d)" && pwd -P)
trap 'rm -rf -- "${TEST_DIR:?}"' EXIT

fail()
{
    printf 'FAIL: %s\n' "$1" >&2
    [[ ! -f $TEST_DIR/out ]] || sed 's/^/  out: /' "$TEST_DIR/out" >&2
    [[ ! -f $TEST_DIR/err ]] || sed 's/^/  err: /' "$TEST_DIR/err" >&2
    exit 1
}

BIN="$TEST_DIR/bin"
LOG="$TEST_DIR/log"
mkdir -p "$BIN" "$LOG"

# --- Fakes -------------------------------------------------------------------
cat > "$BIN/ssh" << 'FAKE'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$LOG/ssh.log"
has_n=false
args=("$@")
for arg in "${args[@]}"; do
    [[ $arg == -n ]] && has_n=true
    if [[ $arg == ControlPath=* ]]; then
        control_dir=$(dirname -- "${arg#ControlPath=}")
        stat -c '%a' "$control_dir" >> "$LOG/control-dir-mode"
    fi
    [[ $arg == -O || $arg == -fN ]] && exit 0
done
[[ $has_n == true ]] || cat > /dev/null
command=${args[${#args[@]} - 1]}
case $command in
    mkdir*) exit 0 ;;
    du*)
        count=$(cat "$LOG/du-count" 2> /dev/null || echo 0)
        echo $((count + 1)) > "$LOG/du-count"
        if [[ $count -eq 0 ]]; then
            printf '%s\n' "${FAKE_DU_BEFORE-100	/x}"
        else
            printf '%s\n' "${FAKE_DU_AFTER-150	/x}"
        fi
        ;;
esac
FAKE

cat > "$BIN/rsync" << 'FAKE'
#!/usr/bin/env bash
src=${*: -2:1}
{ printf '%s\n' "--- call"; printf '%s\n' "$@"; } >> "$LOG/rsync.log"
echo "rsync $src" >> "$LOG/order.log"
if [[ $src == /etc/ ]]; then exit "${FAKE_RC_ETC:-0}"; fi
exit "${FAKE_RC_HOME:-0}"
FAKE

cat > "$BIN/ssh-add" << 'FAKE'
#!/usr/bin/env bash
exit 0
FAKE
cat > "$BIN/hostnamectl" << 'FAKE'
#!/usr/bin/env bash
printf '%s\n' "${FAKE_HOSTNAME-testhost}"
FAKE
cat > "$BIN/id" << 'FAKE'
#!/usr/bin/env bash
printf '%s\n' "${FAKE_USER-tester}"
FAKE
cat > "$BIN/pacman" << 'FAKE'
#!/usr/bin/env bash
case $1 in
    -Qtdq) exit 1 ;;
    -Qqe)
        printf 'alpha\nbeta\n'
        [[ -z ${FAKE_PACMAN_FAIL:-} ]] || exit 1
        ;;
esac
FAKE
cat > "$BIN/yay" << 'FAKE'
#!/usr/bin/env bash
echo "yay $*" >> "$LOG/order.log"
FAKE
chmod +x "$BIN"/*
export LOG
export PATH="$BIN:$PATH"

# --- Harness -----------------------------------------------------------------
OS_RELEASE="$TEST_DIR/os-release"
printf 'ID=arch\n' > "$OS_RELEASE"

reset_case()
{
    local name
    for name in home run tmp repo out err; do
        rm -rf -- "${TEST_DIR:?}/$name"
    done
    rm -rf -- "${LOG:?}"
    mkdir -p "$LOG" "$TEST_DIR"/{home,run,tmp,repo/dist/arch}
    chmod 700 "$TEST_DIR/run"
    echo data > "$TEST_DIR/home/file"
    printf 'x\n' > "$TEST_DIR/repo/dist/test_excludes.txt"
    unset FAKE_DU_BEFORE FAKE_DU_AFTER FAKE_RC_HOME FAKE_RC_ETC \
        FAKE_HOSTNAME FAKE_USER FAKE_PACMAN_FAIL BACKUP_MAX_DELETIONS
}

# Runs the script; its status lands in RC, its output in $TEST_DIR/out|err.
run_backup()
{
    RC=0
    HOME="$TEST_DIR/home" XDG_RUNTIME_DIR="$TEST_DIR/run" TMPDIR="$TEST_DIR/tmp" \
        DOTFILES_REPOSITORY="$TEST_DIR/repo" BACKUP_OS_RELEASE="$OS_RELEASE" \
        bash "$BACKUP" "$@" > "$TEST_DIR/out" 2> "$TEST_DIR/err" < /dev/null || RC=$?
}

assert_out()
{
    grep -qF -- "$1" "$TEST_DIR/out" "$TEST_DIR/err" || fail "$2"
}

assert_no_leftovers()
{
    [[ -z $(ls -A "$TEST_DIR/tmp") ]] || fail "temporary files left in TMPDIR: $(ls -A "$TEST_DIR/tmp")"
    [[ -z $(ls -A "$TEST_DIR/run") ]] || fail "ssh control directory left behind"
}

real_calls()
{
    grep -c '^rsync ' "$LOG/order.log" 2> /dev/null || true
}

# --- 1. One rsync pass per source, no dry run ---------------------------------
reset_case
run_backup
[[ $RC -eq 0 ]] || fail "plain run exited $RC"
[[ $(real_calls) -eq 2 ]] || fail "expected one rsync per source, got $(real_calls)"
[[ $(grep -c '^--- call' "$LOG/rsync.log") -eq 2 ]] || fail "rsync called more than once per source"
if grep -qx -- '--dry-run' "$LOG/rsync.log"; then fail "no dry run expected"; fi
assert_out 'Disk space delta: +50 KB' "disk delta missing"
if grep -q 'Estimated volume' "$TEST_DIR/out"; then fail "volume estimates are gone with the dry run"; fi
assert_no_leftovers

# --- 2. rsync flags, ssh options, quoting ------------------------------------
if grep -qx -- '--no-links' "$LOG/rsync.log"; then fail "--no-links must be gone so symlinks are backed up"; fi
if grep -qx -- '--perms' "$LOG/rsync.log"; then fail "--perms is redundant with --archive"; fi
grep -qx -- '--max-delete=1000' "$LOG/rsync.log" || fail "--max-delete backstop missing"
grep -q 'BatchMode=yes' "$LOG/rsync.log" || fail "rsync ssh lacks BatchMode"
grep -q 'ServerAliveInterval=30' "$LOG/rsync.log" || fail "rsync ssh lacks ServerAliveInterval"
grep -q '"ControlPath=' "$LOG/rsync.log" || fail "ControlPath not quoted"
grep -q -- "^-n " "$LOG/ssh.log" || fail "run_ssh must pass -n"
grep -qF -- "mkdir -p -- '/volume1/NetBackup/testhost/home/tester'" "$LOG/ssh.log" || fail "remote mkdir not quoted"
grep -qF -- "du -s -- '/volume1/NetBackup/testhost'" "$LOG/ssh.log" || fail "remote du not quoted"
grep -qx 700 "$LOG/control-dir-mode" || fail "ssh control directory is not 0700"

# --- 3. rsync statuses: both sources run, worst status wins ----------------
reset_case
FAKE_RC_HOME=24 run_backup
[[ $RC -eq 0 ]] || fail "rsync 24 must only warn, got $RC"
assert_out 'vanished' "rsync 24 warning missing"
assert_out 'Backup completed' "success line missing after 24"

reset_case
FAKE_RC_ETC=23 run_backup
[[ $RC -eq 23 ]] || fail "rsync 23 on /etc must fail the run, got $RC"
[[ $(real_calls) -eq 2 ]] || fail "both sources must run after a failure in the last one"
assert_out 'skips deletions on I/O errors' "rsync 23 explanation missing"
assert_out 'Disk space delta' "summary missing after a failure"
assert_out 'finished with errors' "failure line missing"
assert_no_leftovers

reset_case
FAKE_RC_HOME=12 FAKE_RC_ETC=23 run_backup
[[ $RC -eq 23 ]] || fail "worst status must win, got $RC"
[[ $(real_calls) -eq 2 ]] || fail "a failing first source must not skip the second"

reset_case
FAKE_RC_HOME=12 run_backup
[[ $RC -eq 12 ]] || fail "a failure of the first source must be reported, got $RC"

# --- 4. Mass-deletion guard and empty source ---------------------------------
reset_case
BACKUP_MAX_DELETIONS=5 FAKE_RC_HOME=25 run_backup
[[ $RC -eq 25 ]] || fail "rsync 25 must fail the run, got $RC"
assert_out 'deletion limit (25)' "rsync 25 explanation missing"
grep -qx -- '--max-delete=5' "$LOG/rsync.log" || fail "--max-delete=5 missing"
[[ $(real_calls) -eq 2 ]] || fail "the other source must still run after a 25"

reset_case
BACKUP_MAX_DELETIONS=5 run_backup --force-delete
[[ $RC -eq 0 ]] || fail "--force-delete must pass the guard, got $RC"
if grep -q -- '--max-delete' "$LOG/rsync.log"; then fail "--force-delete must not pass --max-delete"; fi

reset_case
run_backup --max-deletions=30
[[ $RC -eq 0 ]] || fail "--max-deletions=30 must allow 20 deletions, got $RC"
grep -qx -- '--max-delete=30' "$LOG/rsync.log" || fail "--max-delete=30 missing"

reset_case
run_backup --max-deletions=abc
[[ $RC -eq 2 ]] || fail "invalid limit must be a usage error, got $RC"

reset_case
rm -f "$TEST_DIR/home/file"
run_backup
[[ $RC -ne 0 ]] || fail "empty home must fail the run"
assert_out 'missing or empty' "empty source message missing"
[[ $(real_calls) -eq 1 ]] || fail "empty source must not be synced, got $(real_calls) calls"

# --- 5. Identity validation --------------------------------------------------
for bad in '' '../x' 'a b' '-rf' 'a/b'; do
    reset_case
    FAKE_HOSTNAME=$bad run_backup
    [[ $RC -ne 0 ]] || fail "hostname '$bad' accepted"
    [[ ! -f $LOG/rsync.log && ! -f $LOG/ssh.log ]] || fail "hostname '$bad' reached ssh or rsync"
done
reset_case
FAKE_USER='a b' run_backup
[[ $RC -ne 0 ]] || fail "unsafe user accepted"
[[ ! -f $LOG/rsync.log ]] || fail "unsafe user reached rsync"

# --- 6. Disk size validation --------------------------------------------------
reset_case
FAKE_DU_AFTER='oops	/x' run_backup
[[ $RC -eq 0 ]] || fail "non-numeric du must not crash a successful backup, got $RC"
assert_out 'Disk space delta unavailable' "unavailable delta not reported"

# --- 7. Package list ---------------------------------------------------------
reset_case
printf 'old\n' > "$TEST_DIR/repo/dist/arch/pkglist-20200101-000000-arch.txt"
run_backup
[[ $RC -eq 0 ]] || fail "package run exited $RC"
[[ ! -e $TEST_DIR/repo/dist/arch/pkglist-20200101-000000-arch.txt ]] || fail "old baseline kept after a good list"
[[ $(cat "$TEST_DIR"/repo/dist/arch/pkglist-2*-arch.txt) == $'alpha\nbeta' ]] || fail "new list wrong"
ls "$TEST_DIR"/repo/dist/arch/pkglist-*.diff > /dev/null || fail "diff file missing"

reset_case
printf 'old\n' > "$TEST_DIR/repo/dist/arch/pkglist-20200101-000000-arch.txt"
FAKE_PACMAN_FAIL=1 run_backup
[[ $RC -eq 0 ]] || fail "a failing package list must not fail the backup, got $RC"
[[ -f $TEST_DIR/repo/dist/arch/pkglist-20200101-000000-arch.txt ]] || fail "baseline deleted after a failed list"
[[ $(find "$TEST_DIR/repo/dist/arch" -type f | wc -l) -eq 1 ]] || fail "partial list left behind"

reset_case
printf 'ID=plan9\n' > "$OS_RELEASE"
run_backup
printf 'ID=arch\n' > "$OS_RELEASE"
[[ $RC -eq 0 ]] || fail "unknown distribution must be skipped cleanly, got $RC"
assert_out 'Package list skipped' "skip message missing"

# --- 8. Package cleaning only after a successful backup ----------------------
reset_case
run_backup --clean-packages
[[ $RC -eq 0 ]] || fail "clean run exited $RC"
[[ $(tail -n 1 "$LOG/order.log") == 'yay -Sc --noconfirm' ]] || fail "cleaning must come after the backup"

reset_case
FAKE_RC_ETC=23 run_backup --clean-packages
if grep -q '^yay' "$LOG/order.log"; then fail "packages cleaned after a failed backup"; fi
assert_out 'Package cleaning skipped' "skipped-cleaning message missing"

# --- 9. Functions (sourced) --------------------------------------------------
# shellcheck source=/dev/null
source "$BACKUP"
LC_ALL=C

reset_case
printf 'no-newline' > "$TEST_DIR/home/.no_backup.txt"
printf 'second' > "$TEST_DIR/repo/dist/test_excludes.txt"
out_file="$TEST_DIR/excludes"
: > "$out_file"
HOME="$TEST_DIR/home" DOTFILES_REPOSITORY="$TEST_DIR/repo" build_excludes "$out_file"
grep -qx 'no-newline' "$out_file" || fail "excludes merged across files"
grep -qx 'second' "$out_file" || fail "second exclude missing"

if source_is_populated "$TEST_DIR/nope"; then fail "missing dir considered populated"; fi
mkdir "$TEST_DIR/emptydir"
if source_is_populated "$TEST_DIR/emptydir"; then fail "empty dir considered populated"; fi
source_is_populated "$TEST_DIR/home" || fail "populated dir refused"

printf 'backup tests passed\n'
