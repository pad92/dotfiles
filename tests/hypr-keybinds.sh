#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
SCRIPT="$ROOT_DIR/ansible/roles/dotfiles/files/home/.bin/hypr-keybinds.sh"
HYPR_DIR="$ROOT_DIR/ansible/roles/dotfiles/files/home/.config/hypr"
TEST_DIR=$(mktemp -d)
trap 'rm -rf -- "$TEST_DIR"' EXIT

fail()
{
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

# --- Fake Hyprland tools -----------------------------------------------------
# hyprctl prints $FAKE_BINDS (or fails when FAKE_HYPRCTL_FAIL=1); hyprlauncher
# records its arguments and stdin so the test sees what the user would see.
mkdir -p "$TEST_DIR/bin"
cat >"$TEST_DIR/bin/hyprctl" <<'EOF'
#!/usr/bin/env bash
[ "${FAKE_HYPRCTL_FAIL:-0}" = 1 ] && exit 3
[ "$*" = "binds -j" ] || exit 4
printf '%s' "$FAKE_BINDS"
EOF
cat >"$TEST_DIR/bin/hyprlauncher" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >"$LAUNCHER_ARGS"
cat >"$LAUNCHER_INPUT"
EOF
# notify-send must not reach a real notification daemon during tests.
cat >"$TEST_DIR/bin/notify-send" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$NOTIFY_LOG"
EOF
chmod +x "$TEST_DIR/bin/"*
export PATH="$TEST_DIR/bin:$PATH"
export LAUNCHER_ARGS="$TEST_DIR/launcher-args" LAUNCHER_INPUT="$TEST_DIR/launcher-input"
export NOTIFY_LOG="$TEST_DIR/notify.log"

# Fields mirror `hyprctl binds -j` from Hyprland 0.57 with the Lua config.
export FAKE_BINDS='[
  {"modmask": 65, "submap": "", "key": "Q", "keycode": 0, "catch_all": false,
   "has_description": true, "description": "Close window",
   "dispatcher": "HL.Dispatcher(close)", "arg": "7"},
  {"modmask": 76, "submap": "", "key": "Return", "keycode": 0, "catch_all": false,
   "has_description": true, "description": "All three",
   "dispatcher": "HL.Dispatcher(exec_cmd)", "arg": "8"},
  {"modmask": 72, "submap": "", "key": "", "keycode": 10, "catch_all": false,
   "has_description": true, "description": "Move to 1 (stay)",
   "dispatcher": "HL.Dispatcher(move)", "arg": "9"},
  {"modmask": 72, "submap": "", "key": "", "keycode": 90, "catch_all": false,
   "has_description": false, "description": "",
   "dispatcher": "HL.Dispatcher(move)", "arg": "10"},
  {"modmask": 0, "submap": "", "key": "", "keycode": 200, "catch_all": false,
   "has_description": false, "description": "",
   "dispatcher": "exec", "arg": "kitty"},
  {"modmask": 64, "submap": "", "key": "mouse:272", "keycode": 0, "catch_all": false,
   "has_description": true, "description": "Move window",
   "dispatcher": "HL.Dispatcher(drag)", "arg": "11"},
  {"modmask": 0, "submap": "resize", "key": "", "keycode": 0, "catch_all": true,
   "has_description": false, "description": "",
   "dispatcher": "submap", "arg": "reset"},
  {"modmask": 0, "submap": "", "key": "XF86AudioMute", "keycode": 0, "catch_all": false,
   "has_description": true, "description": "",
   "dispatcher": "HL.Dispatcher(exec_cmd)", "arg": "12"}
]'

# --- Each bind becomes one readable line --------------------------------------
expected='SUPER + SHIFT + Q  —  Close window
SUPER + CTRL + ALT + Return  —  All three
SUPER + ALT + 1  —  Move to 1 (stay)
SUPER + ALT + KP_0  —  move
code:200  —  exec kitty
SUPER + Left click  —  Move window
[resize] Any key  —  submap reset
XF86AudioMute  —  exec_cmd'

actual=$("$SCRIPT" --print) || fail "--print failed on valid binds"
[ "$actual" = "$expected" ] || fail "unexpected list:
--- expected
$expected
--- actual
$actual"

# --- Without --print the same list goes to Hyprlauncher in dmenu mode ---------
"$SCRIPT" || fail "opening the launcher failed"
[ "$(cat "$LAUNCHER_ARGS")" = "-m" ] || fail "hyprlauncher was not started in dmenu mode: $(cat "$LAUNCHER_ARGS")"
[ "$(cat "$LAUNCHER_INPUT")" = "$expected" ] || fail "hyprlauncher did not receive the bind list"

# --- Failures exit non-zero and tell the user ---------------------------------
expect_error()
{
    local label="$1" pattern="$2" status
    shift 2
    : >"$NOTIFY_LOG"
    set +e
    "$@" >/dev/null 2>"$TEST_DIR/stderr"
    status=$?
    set -e
    [ "$status" -eq 1 ] || fail "$label: exit status $status, expected 1"
    grep -q -- "$pattern" "$TEST_DIR/stderr" || fail "$label: stderr lacks '$pattern'"
    grep -q -- "$pattern" "$NOTIFY_LOG" || fail "$label: no notification with '$pattern'"
}

expect_error "hyprctl failure" "is Hyprland running" env FAKE_HYPRCTL_FAIL=1 "$SCRIPT" --print
expect_error "invalid JSON" "could not be read" env FAKE_BINDS='not json' "$SCRIPT" --print
expect_error "no binds" "no keybindings" env FAKE_BINDS='[]' "$SCRIPT" --print

rm -f "$LAUNCHER_INPUT"
expect_error "hyprctl failure before the launcher" "is Hyprland running" env FAKE_HYPRCTL_FAIL=1 "$SCRIPT"
[ ! -e "$LAUNCHER_INPUT" ] || fail "hyprlauncher was opened although hyprctl failed"

set +e
"$SCRIPT" --bogus >/dev/null 2>&1
status=$?
set -e
[ "$status" -eq 2 ] || fail "an unknown option exited with $status, expected 2"

# --- The shipped keybindings are all described and SUPER + F1 opens the list --
# The real config is loaded against a stub `hl` that records every bind, so a
# new bind without a description fails here instead of showing up as a bare
# dispatcher name in the list.
command -v lua >/dev/null 2>&1 || fail "lua is required to check keybindings.lua"
HOME="$TEST_DIR" lua - "$HYPR_DIR" <<'EOF' || fail "keybindings.lua check failed"
local hypr_dir = arg[1]
package.path = hypr_dir .. "/?.lua;" .. package.path

-- Any hl.dsp.* chain is callable and returns a marker of its own path.
local function dispatcher(path)
  return setmetatable({}, {
    __index = function(_, key) return dispatcher(path .. "." .. key) end,
    __call = function(_, args) return { path = path, args = args } end,
  })
end

local binds = {}
_G.hl = {
  dsp = dispatcher("dsp"),
  bind = function(keys, action, opts)
    binds[#binds + 1] = { keys = keys, action = action, opts = opts or {} }
  end,
}

local config = require("config")
require("conf.keybindings")

local errors = {}
if #binds == 0 then errors[#errors + 1] = "no bind was registered" end
for _, bind in ipairs(binds) do
  local description = bind.opts.description
  if type(description) ~= "string" or description == "" then
    errors[#errors + 1] = "bind without description: " .. bind.keys
  end
end

local f1 = {}
for _, bind in ipairs(binds) do
  if bind.keys == config.mainMod .. " + F1" then f1[#f1 + 1] = bind end
end
if #f1 ~= 1 then
  errors[#errors + 1] = "expected one SUPER + F1 bind, found " .. #f1
elseif f1[1].action.path ~= "dsp.exec_cmd" or f1[1].action.args ~= config.utils.keybinds then
  errors[#errors + 1] = "SUPER + F1 does not run config.utils.keybinds"
elseif not tostring(config.utils.keybinds):find("hypr-keybinds.sh", 1, true) then
  errors[#errors + 1] = "config.utils.keybinds does not point to hypr-keybinds.sh"
end

if #errors > 0 then
  io.stderr:write(table.concat(errors, "\n") .. "\n")
  os.exit(1)
end
EOF

printf 'hypr-keybinds: all checks passed\n'
