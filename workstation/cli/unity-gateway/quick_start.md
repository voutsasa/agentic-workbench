---
tool: unity-gateway
updated: 2026-09-27
author: Achilleas Voutsas
version: 0.1.0
---

# unity-gateway — quick start

`ug` configures coding agents (Claude Code, Codex, Gemini CLI, OpenCode, Copilot CLI, Pi) to run
**through Databricks AI Gateway**, and registers Databricks MCP servers for those agents. It
authenticates through your [Databricks CLI](../databricks-cli/quick_start.md) login.

> **This workbench uses one `ug` command: `ug mcp-proxy`, as GitHub Copilot CLI's bridge to the
> [Databricks MCP servers](../../mcp/databricks-mcp/setup.md).** Don't set an agent up with
> `ug` on a provider-bound machine. Setting Claude up points its model traffic at Databricks: it
> sets `ANTHROPIC_BASE_URL` and `CLAUDE_CODE_USE_GATEWAY`, and writes
> `~/.claude/ucode-settings.json`, `~/.claude.json` and, on macOS,
> `/Library/Application Support/ClaudeCode/managed-settings.json`.

## The one command used here: `ug mcp-proxy`

```sh
ug mcp-proxy --url "<endpoint>" --host "<workspace-url>" --profile "<profile>"
```

This is a stdio MCP server that relays every message to `--url` and injects a newly minted
Databricks token into every upstream request, so the token never expires mid-session. The client
starts it and stops it; you don't run it yourself. `workstation/scripts/databricks_mcp.py` prints the
`copilot mcp add` line that registers it. How to test it by hand is in the MCP
[`setup.md`](../../mcp/databricks-mcp/setup.md#confirm).

## Read-only commands (safe any time)

```sh
ug --version
ug status                 # workspace, tool configs, live model availability
ug mcp list               # MCP servers ug configured, and whether each is connected
ug --dry-run configure    # print the config files ug would write, without writing them
```

## Commands that write agent config

| Command | Writes |
|---|---|
| `ug configure [--agents claude,codex] [--profile <p>]` | Agent config, so the named agents' models run through AI Gateway |
| `ug claude` (likewise `codex`, `gemini`, …) | Configures that agent if needed, then launches it through Databricks |
| `ug mcp add --names system.ai.genie_one_mcp` | Registers MCP servers for **already-configured** agents |
| `ug mcp add --agents claude --names …` | **Sets Claude up first** ("workspace + models") if it isn't already, then registers the servers |
| `ug mcp remove` | Removes servers `ug` registered |
| `ug revert` | Clears `ug` state and restores the agent config files it backed up |

`ug mcp add` registers each server as a local **stdio** proxy (`ug mcp-proxy`), which refreshes
tokens from your CLI profile. It does not create an HTTP entry.

## Traps

- **`ERROR Claude Code is not available on this workspace. (claude discovery: AI Gateway returned no Claude model ids)`**
  means `ug` tried to set Claude up and found no Claude models in the workspace's AI Gateway. It
  looks in `system.ai` unless you pick another source with `--provider` or `--model-location`.
  This is not an MCP error. The reason is saved under `_discovery_reasons.claude` in
  `~/.ucode/state.json`. The fix is on the workspace side (an admin enables Claude models in AI
  Gateway), or not setting Claude up through `ug` at all.
- **`ug revert` is how to undo it.** If `ug` has written Claude config you didn't want, run
  `ug revert`, not hand-edits. It restores from `~/.ucode/managed-backups/`.
- **`--skip-preflight`** skips the per-launch auth and AI Gateway checks. It hides the error above
  rather than fixing it.
