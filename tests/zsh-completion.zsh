#!/usr/bin/env zsh

set -euo pipefail
ROOT_DIR=${0:A:h:h}
ZSH_TREE=$ROOT_DIR/ansible/roles/dotfiles/files/home/zsh
TEST_DIR=$(mktemp -d)
trap 'rm -rf -- "$TEST_DIR"' EXIT

fail() { print -u2 "FAIL: $1"; exit 1; }

# Every bundled completion must be a completion function. _hugo once held a
# bare $(...) line and was never loaded.
for file in $ZSH_TREE/completions/_*(N); do
  read -r first < $file
  [[ $first == '#compdef '* || $first == '#autoload'* ]] \
    || fail "${file:t} does not start with #compdef"
done

# A bundled copy must not hide the completion shipped by zsh or a package:
# the old _ansible only knew `ansible` and hid zsh's own, which covers every
# Ansible CLI.
default_fpath=($(zsh -fc 'print -r -- $fpath'))
for file in $ZSH_TREE/completions/_*(N); do
  for dir in $default_fpath; do
    [[ -e $dir/${file:t} ]] && fail "completions/${file:t} hides $dir/${file:t}"
  done
done

# Isolated HOME with the zsh tree linked as the dotfiles role deploys it.
mkdir -p "$TEST_DIR/.local/share/dotfiles"
ln -s "$ZSH_TREE" "$TEST_DIR/.local/share/dotfiles/zsh"
cat > "$TEST_DIR/.zshrc" <<'EOF'
ZSH="${HOME}/.local/share/dotfiles/zsh"
ZSH_THEME="pad"
plugins=(httpie)
source "${ZSH}/init.zsh"
EOF

# Fake tools: sops generates its own zsh completion; dottest-bash only ships a
# self-contained bash completion; dottest-helper's bash completion needs the
# bash-completion helpers, which zsh lacks.
mkdir -p "$TEST_DIR/bin" "$TEST_DIR/bash-completions"
cat > "$TEST_DIR/bin/sops" <<'EOF'
#!/bin/sh
[ "$1 $2" = 'completion zsh' ] || exit 1
printf '#compdef sops\n_dottest_sops() { compadd encrypt; }\ncompdef _dottest_sops sops\n'
EOF
print -r -- '#!/bin/sh' > "$TEST_DIR/bin/dottest-bash"
cp "$TEST_DIR/bin/dottest-bash" "$TEST_DIR/bin/dottest-helper"
chmod +x "$TEST_DIR"/bin/*
cat > "$TEST_DIR/bash-completions/dottest-bash" <<'EOF'
_dottest_bash() { COMPREPLY=($(compgen -W 'alpha beta' -- "${COMP_WORDS[COMP_CWORD]}")); }
complete -F _dottest_bash dottest-bash
EOF
cat > "$TEST_DIR/bash-completions/dottest-helper" <<'EOF'
_dottest_helper() { local cur prev words cword; _init_completion || return; }
complete -F _dottest_helper dottest-helper
EOF

start_zsh() {
  HOME=$TEST_DIR ZDOTDIR=$TEST_DIR PATH="$TEST_DIR/bin:$PATH" \
    DOTFILES_BASH_COMPLETION_DIR=$TEST_DIR/bash-completions zsh -i -c '
    print -r -- "${_comps[http]:-NONE} ${fpath[(i)$ZSH/plugins/httpie]} ${fpath[(i)'"${default_fpath[1]}"']}" \
      "${_comps[sops]:-NONE} ${_comps[dottest-bash]:-NONE} ${_comps[dottest-helper]:-NONE}"' \
    2>/dev/null | tail -n 1
}

for run in first cached; do
  result=(${(z)$(start_zsh)})
  [[ ${result[1]} == _httpie ]] \
    || fail "$run start: plugin completions are not on fpath before compinit (got: $result)"
  (( result[2] > result[3] )) \
    || fail "$run start: plugin directories come before the zsh and package completions"
  [[ ${result[4]} != NONE ]] \
    || fail "$run start: sops has no completion (packaged or generated)"
  [[ ${result[5]} == _dotfiles_bash_completion ]] \
    || fail "$run start: a bash-only completion is not loaded through bashcompinit (got: $result)"
  [[ ${result[6]} == NONE ]] \
    || fail "$run start: a bash completion that needs bash-completion helpers was loaded"
done
[[ -s $TEST_DIR/.zcache/bash-completions ]] \
  || fail 'the list of usable bash completions was not cached'

# Host names: ssh_config syntax, Includes and known_hosts formats.
SSH_HOME=$TEST_DIR/ssh-home
mkdir -p "$SSH_HOME/.ssh/conf.d"
cat > "$SSH_HOME/.ssh/config" <<'EOF'
Host *
    ServerAliveInterval 30
host lower-host
Host=equal-host
  Host indented-host multi-a !negated wild-* q?
Match originalhost match-host user foo
Include conf.d/*
Include ~/.ssh/abs.conf
EOF
printf 'Host included-host\nInclude conf.d/loop\n' > "$SSH_HOME/.ssh/conf.d/loop"
printf 'HOST abs-host\n' > "$SSH_HOME/.ssh/abs.conf"
cat > "$SSH_HOME/.ssh/known_hosts" <<'EOF'
kh-a,kh-b ssh-ed25519 AAAA
[kh-port]:2222 ssh-ed25519 AAAA
|1|hashed=|xyz= ssh-ed25519 AAAA
@cert-authority *.example.test ssh-ed25519 AAAA
@revoked kh-revoked ssh-ed25519 AAAA
EOF
hosts=(${(f)"$(HOME=$SSH_HOME zsh -fc '
  source <(sed -n "/^_dotfiles_hosts() {/,/^}/p" "$1"); _dotfiles_hosts; print -rl -- $reply' \
  _ "$ZSH_TREE/init/completion.zsh")"})
for name in lower-host equal-host indented-host multi-a match-host included-host abs-host kh-a kh-b kh-port; do
  (( ${hosts[(Ie)$name]} )) || fail "host completion misses $name"
done
for name in '!negated' 'wild-*' 'q?' negated '*.example.test' kh-revoked '[kh-port]:2222'; do
  (( ${hosts[(Ie)$name]} )) && fail "host completion offers $name"
done
included=(${(M)hosts:#included-host})
(( $#included == 1 )) || fail 'an Include loop repeats hosts'

print 'PASS: zsh registers plugin, generated, bash-only and ssh host completions without hiding the packaged ones'
