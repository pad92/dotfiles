# agent_cli

This role configures the AI coding agents installed on the host: the status
line of Claude Code and Codex, and token-saving settings for Claude Code. It
changes only the keys it names in each tool's own configuration file and
leaves the rest of that file as it is. The status line script is deployed by the
`dotfiles` role.

Both playbook tags, `dotfiles` and `agent_cli`, run the role.

## Requirements

- Runs as the user, without privilege escalation.
- The `dotfiles` role deploys `~/.bin/claude-statusline`.

## Role Variables

| Variable                            | Default                                           | Description                                               |
| :---------------------------------- | :------------------------------------------------ | :-------------------------------------------------------- |
| `agent_cli_home`                    | the SSH user's home                               | Home directory of the configured tools.                   |
| `agent_cli_claude_binary`           | `claude`                                          | Claude Code is configured only when this binary is found. |
| `agent_cli_claude_settings`         | `.claude/settings.json`                           | Settings file, relative to the home.                      |
| `agent_cli_claude_statusline`       | command `~/.bin/claude-statusline`                | Value of the `statusLine` key.                            |
| `agent_cli_claude_env`              | autocompact at 60 %, no 1M context, tool search   | Variables merged into the `env` table.                    |
| `agent_cli_claude_enabled_plugins`  | `frontend-design`, `humanizer`                    | Entries merged into `enabledPlugins`.                     |
| `agent_cli_claude_permissions_deny` | `Read` of `node_modules`, `.venv`, `__pycache__`  | Entries added to `permissions.deny`.                      |
| `agent_cli_claude_state`            | `.claude.json`                                    | Claude Code state file, relative to the home.             |
| `agent_cli_claude_mcp_absent`       | `caveman`                                         | User-scope MCP servers removed when present.              |
| `agent_cli_codex_binary`            | `codex`                                           | Codex is configured only when this binary is found.       |
| `agent_cli_codex_config`            | `.codex/config.toml`                              | Codex configuration, relative to the home.                |
| `agent_cli_codex_status_line`       | model, directory, branch, context, tokens, limits | Items of `[tui] status_line`.                             |

## Claude Code status line

The `dotfiles_claude` tag adds the `statusLine` key to `~/.claude/settings.json`
only when `agent_cli_claude_binary` (`claude` by default) is found in `PATH` or
`~/.local/bin`. Otherwise nothing is created or changed. Other settings, their
order and the file mode are kept. A new file is created with mode `0600`. The
role never versions this file because it also holds local permissions and
project context. A file that is not a JSON object stops the play unchanged.
Override `agent_cli_claude_statusline` to change the command or add options such
as `padding` or `refreshInterval`.

## Claude Code token-saving settings

The same tag also merges `agent_cli_claude_env`, `agent_cli_claude_enabled_plugins`
and `agent_cli_claude_permissions_deny` into `~/.claude/settings.json`. Each key
listed in a variable is rewritten on every run. The other entries of `env` and
`enabledPlugins`, and the other `permissions` entries, are kept. The deny list
is appended to the existing one without duplicates. A variable of another type
in the file stops the play unchanged.

The role does not manage the `OTEL_*` variables, so their credentials never
enter the repository.

For each name in `agent_cli_claude_mcp_absent` found in `mcpServers` of
`~/.claude.json`, the role runs `claude mcp remove NAME --scope user`. It never
edits that file itself because Claude Code rewrites it at any time. Nothing runs
in check mode or when the server is absent.

## Codex status line

Codex has no external status line command: it draws a list of built-in items.
The `dotfiles_codex` tag writes `agent_cli_codex_status_line` to `status_line`
in the `[tui]` table of `~/.codex/config.toml` only when `agent_cli_codex_binary`
(`codex` by default) is found. The default shows the model and reasoning
effort, directory, branch, context used, tokens, then the 5-hour and weekly
limits. Codex ignores an unknown item with a warning at startup.

Only that key is touched: trusted projects, comments and the tables Codex
maintains stay as they are, and a value already equal, even on several lines,
is left alone. A file that is not valid TOML stops the play unchanged. If the
existing key cannot be edited in place (an array on several lines, or
`tui.status_line` outside the table), the file is restored and the play fails.
A new file is created with mode `0600`.

## Dependencies

None. The `dotfiles` role deploys the status line script.

## Example Playbook

```yaml
- hosts: all
  roles:
    - role: agent_cli
      become: false
      tags: [agent_cli]
```

## License

Unlicense

## Author Information

pad
