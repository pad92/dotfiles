# agent_cli

Configures the AI coding agents installed on the host: the Claude Code and
Codex status lines, the token-saving settings of Claude Code, and the RTK
output filter. The role changes only the keys it names in each tool's own
configuration file and keeps the rest of the file.

## Requirements

- Runs as the user, without privilege escalation.
- The `dotfiles` role deploys `~/.bin/claude-statusline`.
- Each tool is configured only when its binary is found in `PATH` or in
  `~/.local/bin`. Otherwise the role creates and changes nothing for it.
- RTK is installed only on x86_64 hosts.

## Role Variables

| Variable                            | Default                                                                                                      | Description                                               |
| :---------------------------------- | :----------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------- |
| `agent_cli_home`                    | `"{{ ansible_facts['user_dir'] }}"`                                                                          | Home directory of the configured tools.                   |
| `agent_cli_claude_binary`           | `claude`                                                                                                     | Claude Code is configured only when this binary is found. |
| `agent_cli_claude_settings`         | `.claude/settings.json`                                                                                      | Settings file, relative to the home.                      |
| `agent_cli_claude_statusline`       | `{type: command, command: '{{ agent_cli_home }}/.bin/claude-statusline'}`                                    | Value of the `statusLine` key.                            |
| `agent_cli_claude_env`              | `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: '60'`, `CLAUDE_CODE_DISABLE_1M_CONTEXT: '1'`, `ENABLE_TOOL_SEARCH: 'true'` | Variables merged into the `env` table.                    |
| `agent_cli_claude_enabled_plugins`  | `frontend-design@claude-plugins-official: true`, `humanizer@humanizer: true`                                 | Entries merged into `enabledPlugins`.                     |
| `agent_cli_claude_permissions_deny` | `Read(**/node_modules/**)`, `Read(**/.venv/**)`, `Read(**/__pycache__/**)`                                   | Entries appended to `permissions.deny`.                   |
| `agent_cli_claude_state`            | `.claude.json`                                                                                               | Claude Code state file, relative to the home.             |
| `agent_cli_claude_mcp_absent`       | `[caveman]`                                                                                                  | User-scope MCP servers removed when present.              |
| `agent_cli_rtk_enabled`             | `true`                                                                                                       | Install RTK and merge its Claude Code hook.               |
| `agent_cli_rtk_version`             | `1.2.0`                                                                                                      | Pinned rtk-oss release.                                   |
| `agent_cli_rtk_asset`               | `rtk-oss-x86_64-unknown-linux-musl.tar.gz`                                                                   | Release archive.                                          |
| `agent_cli_rtk_checksum`            | pinned SHA-256, see `defaults/main.yml`                                                                      | Checksum of the archive, checked before install.          |
| `agent_cli_rtk_url`                 | `https://github.com/rtk-ai/rtk/releases/download/v{{ agent_cli_rtk_version }}/{{ agent_cli_rtk_asset }}`     | Download URL.                                             |
| `agent_cli_rtk_bin_dir`             | `'{{ agent_cli_home }}/.local/bin'`                                                                          | Where the `rtk` binary is installed.                      |
| `agent_cli_rtk_hook_command`        | `'{{ agent_cli_rtk_bin_dir }}/rtk hook claude'`                                                              | Command of the `PreToolUse` hook.                         |
| `agent_cli_codex_binary`            | `codex`                                                                                                      | Codex is configured only when this binary is found.       |
| `agent_cli_codex_config`            | `.codex/config.toml`                                                                                         | Codex configuration, relative to the home.                |
| `agent_cli_codex_status_line`       | `[model-with-reasoning, current-dir, git-branch, context-used, used-tokens, five-hour-limit, weekly-limit]`  | Items of `[tui] status_line`.                             |

The role also reads the `user_dir` and `architecture` facts. `site.yml`
gathers them as the SSH user.

## Claude Code status line

The role adds the `statusLine` key to `~/.claude/settings.json`. Other
settings and their order are kept, and so is the mode of an existing file. A
new file gets mode `0600` in a `0700` directory. The role never versions this
file because it also holds local permissions and project context. A file that
is not a JSON object stops the play before any change. Override
`agent_cli_claude_statusline` to change the command or to add options such as
`padding` or `refreshInterval`.

## Claude Code token-saving settings

The same tasks merge `agent_cli_claude_env`, `agent_cli_claude_enabled_plugins`
and `agent_cli_claude_permissions_deny` into `~/.claude/settings.json`. Each
key listed in a variable is rewritten on every run. The other entries of `env`
and `enabledPlugins`, and the other `permissions` entries, are kept. The deny
list is appended to the existing one without duplicates. A key of another type
in the file stops the play before any change.

The role does not manage the `OTEL_*` variables, so their credentials never
enter the repository.

For each name of `agent_cli_claude_mcp_absent` found in `mcpServers` of
`~/.claude.json`, the role runs `claude mcp remove NAME --scope user`. It never
edits that file itself, because Claude Code rewrites it at any time. Nothing
runs in check mode or when the server is absent.

## RTK output filter

RTK ([rtk-ai/rtk](https://github.com/rtk-ai/rtk)) rewrites Bash commands so
that Claude Code reads condensed output. On x86_64, the role installs the
pinned `rtk-oss` release (Apache-2.0) in `agent_cli_rtk_bin_dir` after checking
its SHA-256 checksum, and only when the installed version differs. To upgrade,
change the version and the checksum together.

Under the same conditions, the role also appends a `PreToolUse` hook
(`matcher: Bash`, command `agent_cli_rtk_hook_command`) to `settings.json`,
unless that command is already present. Other hooks are kept. The role does
not run `rtk init`, so `RTK.md` and `CLAUDE.md` stay unchanged. Check the
result with `rtk gain` after restarting Claude Code.

Setting `agent_cli_rtk_enabled: false` stops the install and the hook merge,
but removes neither the binary nor a hook written by an earlier run.

## Codex status line

Codex has no external status line command and draws a list of built-in items
instead. The role writes `agent_cli_codex_status_line` to `status_line` in the
`[tui]` table of `~/.codex/config.toml`. The default shows the model and
reasoning effort, the directory, the branch, the context used, the tokens, and
the 5-hour and weekly limits. Each item must match `^[a-z0-9-]+$`, or the play
stops.

Only that key changes. Trusted projects, comments and the tables Codex
maintains stay as they are, and a value that is already equal, even on several
lines, is left alone. A file that is not valid TOML stops the play before any
change. If the existing key cannot be edited in place (an array on several
lines, or `tui.status_line` outside the table), the file is restored and the
play fails. An existing file keeps its mode; a new one gets `0600`.

## Tags

Both playbook tags, `dotfiles` and `agent_cli`, run the whole role. Inside it:

- `dotfiles_rtk` installs the RTK binary only. The hook is merged by the
  Claude Code tasks, so this tag alone does not add it.
- `dotfiles_claude` runs the RTK install and every Claude Code task, hook
  included.
- `dotfiles_codex` runs the Codex tasks.

## Dependencies

None. In `site.yml` the role runs after `audio` and before `obs`, and relies
on the `dotfiles` role for the status line script.

## Example Playbook

```yaml
- name: Configure the Linux workstations
  hosts: all
  become: true
  roles:
    - role: agent_cli
      become: false
      tags: [dotfiles, agent_cli]
```

## License

Unlicense

## Author Information

pad
