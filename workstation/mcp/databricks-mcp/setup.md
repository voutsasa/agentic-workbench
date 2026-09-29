---
server: databricks-mcp
package: none — hosted endpoints (Copilot CLI bridge: unity-gateway `ug mcp-proxy`)
transport: http
version_observed: n/a (hosted, no local version)
verified: 2026-09-29
pinned: false
---

# databricks-mcp — setup

Databricks' managed MCP servers are published as **MCP services** in the workspace's `system.ai`
Unity Catalog schema. This guide covers their registration for **Claude Code** and **GitHub Copilot
CLI**. The service catalog is workspace-specific and changes while Databricks labels managed MCP
servers **Public Preview**, so commands are generated from the live catalog rather than copied from a
fixed service list.

Verified against Databricks' [managed MCP servers page](https://docs.databricks.com/aws/en/generative-ai/mcp/managed-mcp),
[Genie One page](https://docs.databricks.com/aws/en/agents/mcp-tools/genie-mcp) and
[MCP Services page](https://docs.databricks.com/aws/en/agents/mcp-tools/mcp-services), Claude
Code's [MCP docs](https://code.claude.com/docs/en/mcp), `copilot mcp add --help`, and the
[Unity Gateway README](https://github.com/databricks/unity-gateway), on 29 September 2026.

## The servers

The generator runs this read-only catalog query:

```sh
databricks api get '/api/2.1/unity-catalog/mcp-services?parent=schemas/system.ai&view=BASIC' -p "$DBX_PROFILE" -o json
```

It selects only names shaped as `mcp-services/system.ai.<service>` whose configuration has an
`internal` key. Those services authenticate with the Databricks CLI token. Connection-backed SaaS
services are excluded because they need separate per-user sign-in. If a named service is absent or no
longer internal, the generator refuses to print an add command rather than producing a broken entry.

The catalog's shape and size are workspace-specific and change over time; a snapshot from one machine
is recorded in that machine's file under [`../../machines/`](../../machines/), never here — run the
generator against your own profile rather than assuming a fixed service list.

## Parameters

| Variable | What it is | Where to get it | This workbench |
| --- | --- | --- | --- |
| `DBX_PROFILE` | Databricks CLI profile that holds your login | `databricks auth describe` → `profile` | Set locally; never copy another machine's value |
| `DBX_HOST` | Workspace URL, no trailing slash | `databricks auth describe -p "$DBX_PROFILE"` → `host` | Resolved by the generator |
| `DBX_WORKSPACE_ID` | Numeric workspace ID, sent as `?o=` | `databricks auth describe -p "$DBX_PROFILE"` → `workspace_id` | Resolved by the generator |
| `SERVICE` | An available internal service | The generator's catalog query | Workspace-specific |

Server names are always `databricks-<service>`, so a tool shows up as
`mcp__databricks-<service>__<tool>` in Claude Code.

The endpoint for every service is:

```
$DBX_HOST/ai-gateway/mcp-services/system.ai.$SERVICE?o=$DBX_WORKSPACE_ID
```

The variables use a `DBX_` prefix on purpose. The Databricks CLI reads `DATABRICKS_HOST` and similar
names from the environment, so a leftover `DATABRICKS_*` variable would change which workspace
authenticates.

## Authentication

**One login, for every server and both clients.** You log in to the Databricks CLI once, through
OAuth in the browser (user to machine, U2M). Each client then gets a current token from that login
every time it connects. The two clients differ only in how they fetch the token:

| | Claude Code | Copilot CLI |
| --- | --- | --- |
| Entry type | `http`, straight to the endpoint | `stdio`: a local process that relays to the endpoint (`ug mcp-proxy`) |
| How the token is fetched | `headersHelper` runs `databricks auth token` on every connect, and again after a `401`/`403` | `ug mcp-proxy` gets a fresh token for every upstream request |
| Why | Claude Code supports a command that generates headers | Copilot CLI's config takes **only static headers** (`--header`), and a pasted token expires within the hour |
| Extra tool | `jq` | [`ug`](../../cli/unity-gateway/install.md) |
| Config written | `~/.claude.json`, under this repo's path (`-s local`) | `~/.copilot/mcp-config.json` (user config) |

Common to both:

| Aspect | Detail |
| --- | --- |
| Identity | **You.** Unity Catalog decides what each call can read or change. Account users hold `EXECUTE` on `system.ai` by default. |
| Credential store | The profile is in `~/.databrickscfg` (`auth_type = databricks-cli`), and the tokens are in the CLI's own cache. Neither is in the repo. |
| Token lifetime | About an hour (the `expiry` field of `databricks auth token`), refreshed silently while the login is valid |
| OAuth scope | `databricks auth login` requests `all-apis` by default, which worked for every group A service. Databricks documents `ai-gateway` for on-behalf-of access; if you log in with a narrower `--scopes`, include it. |
| Not used | Personal access tokens, a static `Authorization` header, and a Databricks OAuth app or client ID |

## Prerequisites

| Need | For | Install | Check |
| --- | --- | --- | --- |
| Databricks CLI, logged in | both | [`../../cli/databricks-cli/install.md`](../../cli/databricks-cli/install.md), then `databricks auth login --host "$DBX_HOST"` | `databricks auth profiles` → `Valid YES` |
| `jq` | Claude Code | preinstalled on macOS | `command -v jq` |
| `ug` | Copilot CLI | [`../../cli/unity-gateway/install.md`](../../cli/unity-gateway/install.md) | `ug --version` |

## Register

**The script reads the catalog and prints registration commands; it runs no registration command.**
Review its output, then run the command you choose yourself:

```sh
python workstation/scripts/databricks_mcp.py --profile "$DBX_PROFILE"             # all available internal services, both clients
python workstation/scripts/databricks_mcp.py --profile "$DBX_PROFILE" --client copilot
python workstation/scripts/databricks_mcp.py --profile "$DBX_PROFILE" --remove --service <stale-service>
```

The script reads the host and workspace ID with `databricks auth describe` unless you pass `--host`
and `--workspace-id`, and lists internal services on every add operation. `--remove` deliberately
requires an explicit `--service` and does not query the catalog, so an entry for a retired service can
still be removed. `--claude-scope user` registers the Claude servers for every project, not just this
one. On macOS outside the venv, the command is `python3`
([`../../scripts/README.md`](../../scripts/README.md)).

Do not pipe generated output straight to a shell. The generated Claude command uses `headersHelper`;
the generated Copilot command uses `ug mcp-proxy` and writes to `~/.copilot/mcp-config.json`.

### Confirm

| Client | Command | Expect |
| --- | --- | --- |
| Claude Code | `claude mcp get databricks-<service>` | `Status: ✔ Connected` |
| Copilot CLI | `copilot mcp get databricks-<service>` | `Status: Enabled`, `Command: ug mcp-proxy …` |

`copilot mcp get` reports configuration only; it does not connect. Unity Gateway documents
`ug mcp-proxy` as agent-managed rather than interactive, so do not use a piped `initialize` request as
connection evidence. Restart Copilot, confirm the generated service's tools appear, then invoke an
approved read-only tool request to prove the connection. A running session keeps the servers it loaded
at startup; in Claude Code, reconnect with `/mcp`.

### Why not the shared catalog or `.mcp.json`

None of these servers are in [`../.mcp.json`](../.mcp.json), and `link_config.py --mcp` doesn't
manage them. Every entry depends on **each person's own** CLI profile, so a tracked entry would fail
for anyone without it. The repo's `.mcp.json` is also read by *both* clients (workspace scope), and
they need different entry types for the same server. Claude's `-s local` and Copilot's user config
keep each person's registration private.

## Unity Gateway (`ug`): the Copilot bridge, not a setup tool here

This family uses exactly one `ug` command, `ug mcp-proxy`, as Copilot's bridge. Don't use `ug`'s
setup commands on Claude Code:

- **`ug claude`, `ug configure --agents claude` and `ug mcp add --agents claude` can send Claude
  Code's *model* traffic through Databricks AI Gateway.** An agent named in `--agents` that isn't
  configured yet "is set up first (workspace + models)". Setting Claude up sets
  `ANTHROPIC_BASE_URL` and `CLAUDE_CODE_USE_GATEWAY`, and writes `~/.claude/ucode-settings.json`,
  `~/.claude.json` and, on macOS, `/Library/Application Support/ClaudeCode/managed-settings.json`.
  On a provider-bound machine, that replaces the configuration you are required to run under.
- **This is what produces the error below.** When `ug` sets Claude up, it first checks which Claude
  models the workspace's AI Gateway offers. When there are none, it stops:

  ```
  ERROR Claude Code is not available on this workspace. (claude discovery: AI Gateway returned no Claude model ids)
  ```

  It is not an MCP error. The reason is saved under `_discovery_reasons.claude` in
  `~/.ucode/state.json`. The script above needs no Claude models in the gateway.
- **`ug mcp add --agents copilot` does the same kind of setup for Copilot.** It points Copilot's
  models at Databricks. Register Copilot servers with the `copilot mcp add` line the script prints
  instead.

## Traps

- **Service availability and tool effects change by workspace.** The generator prevents registration
  of unavailable internal services, not unsafe tool calls. Treat every newly discovered tool as
  potentially read/write until its current Databricks documentation and Unity Catalog permissions have
  been checked.
- **A Claude `headersHelper` doesn't run until the folder is trusted.** That applies to local scope
  too. In a folder you haven't accepted the trust dialog for, `claude mcp get` prints
  `headersHelper not run — this workspace has no persisted trust` and then `✘ Failed to connect`.
  Open Claude Code there once and accept the dialog.
- **`401 … Credential was not sent or was of an unsupported type`** means a static
  `headers.Authorization` holds something that isn't a valid token — e.g. the literal string `Bearer ~`
  left over from a bad paste. Remove the entry and register it again from the script's output.
- **Everything fails after the CLI login expires.** `databricks auth profiles` then shows
  `Valid NO`. Run `databricks auth login -p "$DBX_PROFILE"` again.
- **Keep the `?o=<workspace-id>` query string.** Every endpoint was verified with it, and the form
  without it hasn't been tested here.
- **Never commit a token**, in `.mcp.json` or anywhere else. Neither route needs one written down.

Docs: [Managed MCP servers](https://docs.databricks.com/aws/en/generative-ai/mcp/managed-mcp) ·
[Genie One](https://docs.databricks.com/aws/en/agents/mcp-tools/genie-mcp) ·
[MCP Services](https://docs.databricks.com/aws/en/agents/mcp-tools/mcp-services) ·
[Claude Code `headersHelper`](https://code.claude.com/docs/en/mcp) ·
[Copilot CLI MCP servers](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers) ·
full page ingest: [reference.md](reference.md)
