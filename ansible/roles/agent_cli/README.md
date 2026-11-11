# agent_cli role

This role configures the status line of the AI coding agents installed on the
host. It changes one setting in each tool's own configuration file and leaves
the rest of that file as it is. The status line script is deployed by the
`dotfiles` role.

Both playbook tags, `dotfiles` and `agent_cli`, run the role. It runs as the
user, without privilege escalation.

## Claude Code status line

The `dotfiles_claude` tag adds the `statusLine` key to `~/.claude/settings.json`
only when `agent_cli_claude_binary` (`claude` by default) is found in `PATH` or
`~/.local/bin`. Otherwise nothing is created or changed. Other settings, their
order and the file mode are kept. A new file is created with mode `0600`. The
role never versions this file because it also holds local permissions and
project context. A file that is not a JSON object stops the play unchanged.
Override `agent_cli_claude_statusline` to change the command or add options such
as `padding` or `refreshInterval`.

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
