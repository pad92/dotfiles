#!/usr/bin/env bash
#
# Integration tests for vault-toggle. They run the real ansible-vault, so each
# check proves which password actually encrypted the file, not only which
# arguments the script built.

set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
SCRIPT="$ROOT_DIR/ansible/roles/dotfiles/files/home/.bin/vault-toggle"
TEST_DIR=$(cd -- "$(mktemp -d)" && pwd -P)
trap 'rm -rf -- "$TEST_DIR"' EXIT

fail()
{
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

command -v ansible-vault >/dev/null || fail "ansible-vault is required"

# Keep the user's Ansible and Git configuration out of every check.
unset ANSIBLE_CONFIG ANSIBLE_VAULT_PASSWORD_FILE ANSIBLE_VAULT_IDENTITY_LIST
export HOME="$TEST_DIR/home"
export ANSIBLE_LOCAL_TEMP="$TEST_DIR/ansible-tmp"
export GIT_CONFIG_NOSYSTEM=1
mkdir -p "$HOME" "$ANSIBLE_LOCAL_TEMP"
cd "$TEST_DIR"

PLAIN_TEXT=$'secret_token: s3cr3t-value\nother: 1\n'

new_case()
{
    CASE_DIR="$TEST_DIR/$1"
    mkdir -p "$CASE_DIR/project/group_vars"
    TARGET="$CASE_DIR/project/group_vars/vault.yml"
    printf '%s' "$PLAIN_TEXT" >"$TARGET"
}

write_password()
{
    printf '%s\n' "$2" >"$1"
    chmod 600 "$1"
}

is_encrypted()
{
    # shellcheck disable=SC2016 # the literal header text, not a variable
    [[ $(head -n 1 "$1") == '$ANSIBLE_VAULT;'* ]]
}

# Succeeds only when PASSWORD decrypts FILE back to the original plain text.
decrypts_with()
{
    local file=$1 password=$2 pass_file="$TEST_DIR/check-pass"
    write_password "$pass_file" "$password"
    [[ $(ansible-vault view --vault-password-file "$pass_file" "$file" 2>/dev/null) \
        == "${PLAIN_TEXT%$'\n'}" ]]
}

toggle()
{
    "$SCRIPT" "$@" >/dev/null 2>"$TEST_DIR/stderr" </dev/null
}

# --- Round trip with the nearest password file ------------------------------
new_case roundtrip
write_password "$CASE_DIR/.vault" far-password
write_password "$CASE_DIR/project/.vault_pass" near-password
toggle "$TARGET" || fail "encrypting a plain file failed: $(<"$TEST_DIR/stderr")"
is_encrypted "$TARGET" || fail "the file was not encrypted"
grep -q s3cr3t "$TARGET" && fail "the secret is still readable after encryption"
decrypts_with "$TARGET" near-password \
    || fail "the nearest password file was not the one used"
toggle "$TARGET" || fail "decrypting failed: $(<"$TEST_DIR/stderr")"
[[ $(<"$TARGET") == "${PLAIN_TEXT%$'\n'}" ]] \
    || fail "the decrypted content differs from the original"
[[ $(stat -c '%a' "$TARGET") == 600 ]] \
    || fail "the decrypted file is readable by others"
printf 'PASS: vault-toggle round trip with the nearest password file\n'

# --- ANSIBLE_VAULT_PASSWORD_FILE wins over the walked-up file ----------------
new_case env-precedence
write_password "$CASE_DIR/project/.vault" tree-password
write_password "$CASE_DIR/env-pass" env-password
ANSIBLE_VAULT_PASSWORD_FILE="$CASE_DIR/env-pass" toggle "$TARGET" \
    || fail "encrypting with the environment password failed: $(<"$TEST_DIR/stderr")"
decrypts_with "$TARGET" env-password \
    || fail "ANSIBLE_VAULT_PASSWORD_FILE did not take precedence"
printf 'PASS: vault-toggle honours ANSIBLE_VAULT_PASSWORD_FILE\n'

# --- The project's ansible.cfg wins over the walked-up file ------------------
new_case cfg-precedence
write_password "$CASE_DIR/project/.vault" tree-password
write_password "$CASE_DIR/cfg-pass" cfg-password
printf '[defaults]\nvault_password_file = %s\n' "$CASE_DIR/cfg-pass" \
    >"$CASE_DIR/project/ansible.cfg"
(cd "$CASE_DIR/project" && toggle "$TARGET") \
    || fail "encrypting with the ansible.cfg password failed: $(<"$TEST_DIR/stderr")"
decrypts_with "$TARGET" cfg-password \
    || fail "vault_password_file from ansible.cfg did not take precedence"
printf 'PASS: vault-toggle honours vault_password_file in ansible.cfg\n'

# --- Unsafe password files are never used, executable ones never run ---------
new_case untrusted
marker="$CASE_DIR/executed"
printf '#!/bin/sh\ntouch %q\necho planted\n' "$marker" >"$CASE_DIR/project/.vault"
chmod 700 "$CASE_DIR/project/.vault"
write_password "$CASE_DIR/project/group_vars/.vault_pass" shared-password
chmod 660 "$CASE_DIR/project/group_vars/.vault_pass"
write_password "$CASE_DIR/.vault" safe-password
toggle "$TARGET" || fail "encrypting past unsafe password files failed: $(<"$TEST_DIR/stderr")"
[[ -e $marker ]] && fail "an executable password file found in the tree was run"
decrypts_with "$TARGET" safe-password \
    || fail "an executable or group-writable password file was used"
grep -q 'ignoring .*/group_vars/.vault_pass' "$TEST_DIR/stderr" \
    || fail "the group-writable password file was skipped silently"
printf 'PASS: vault-toggle skips executable and group-writable password files\n'

# --- No password source falls back to the interactive prompt -----------------
# A prompt needs a terminal, so a shim records the arguments instead.
new_case prompt
mkdir -p "$CASE_DIR/bin"
cat >"$CASE_DIR/bin/ansible-vault" <<EOF
#!/bin/sh
printf '%s\n' "\$@" >"$CASE_DIR/args"
EOF
chmod 755 "$CASE_DIR/bin/ansible-vault"
PATH="$CASE_DIR/bin:$PATH" toggle "$TARGET" \
    || fail "the prompt fallback failed: $(<"$TEST_DIR/stderr")"
[[ $(<"$CASE_DIR/args") == $'encrypt\n--ask-vault-pass\n--\n'"$TARGET" ]] \
    || fail "without a password source the prompt was not requested: $(<"$CASE_DIR/args")"
printf 'PASS: vault-toggle prompts when no password source exists\n'

# --- Decryption refuses files Git would commit -------------------------------
new_case git
write_password "$CASE_DIR/project/.vault" git-password
git -C "$CASE_DIR/project" init -q
toggle "$TARGET" || fail "encrypting inside a Git repository failed"
encrypted=$(<"$TARGET")

set +e
toggle "$TARGET"; status=$?
set -e
[[ $status == 2 ]] || fail "decrypting a non-ignored file returned $status, not 2"
[[ $(<"$TARGET") == "$encrypted" ]] || fail "a non-ignored file was decrypted"

printf 'group_vars/vault.yml\n' >"$CASE_DIR/project/.gitignore"
git -C "$CASE_DIR/project" add -f group_vars/vault.yml
set +e
toggle "$TARGET"; status=$?
set -e
[[ $status == 2 ]] || fail "decrypting a tracked file returned $status, not 2"
[[ $(<"$TARGET") == "$encrypted" ]] || fail "a tracked, ignored file was decrypted"

toggle --force "$TARGET" || fail "--force did not allow decryption"
is_encrypted "$TARGET" && fail "--force left the file encrypted"

git -C "$CASE_DIR/project" rm -q -f --cached group_vars/vault.yml
toggle "$TARGET" || fail "an ignored, untracked file could not be encrypted"
toggle "$TARGET" \
    || fail "an ignored, untracked file could not be decrypted: $(<"$TEST_DIR/stderr")"
is_encrypted "$TARGET" && fail "an ignored, untracked file was not decrypted"
printf 'PASS: vault-toggle only decrypts files Git ignores\n'

# --- Invalid usage is rejected before ansible-vault runs ---------------------
new_case usage
write_password "$CASE_DIR/project/.vault" usage-password
rejects()
{
    local status
    set +e
    toggle "$@"; status=$?
    set -e
    [[ $status == 2 ]]
}
rejects || fail "a missing FILE was accepted"
rejects "$TARGET" "$TARGET" || fail "two files were accepted"
rejects "$CASE_DIR/missing.yml" || fail "a missing file was accepted"
rejects "$CASE_DIR/project" || fail "a directory was accepted"
rejects --bogus "$TARGET" || fail "an unknown option was accepted"
[[ $(<"$TARGET") == "${PLAIN_TEXT%$'\n'}" ]] || fail "a rejected call changed the file"

dash_file="$CASE_DIR/project/-dash.yml"
printf '%s' "$PLAIN_TEXT" >"$dash_file"
(cd "$CASE_DIR/project" && toggle -- -dash.yml) \
    || fail "a file name starting with a dash failed: $(<"$TEST_DIR/stderr")"
is_encrypted "$dash_file" || fail "a file name starting with a dash was not encrypted"
printf 'PASS: vault-toggle rejects invalid usage\n'
