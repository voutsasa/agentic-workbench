---
server: databricks-mcp
package: none — hosted endpoints (Copilot CLI bridge: unity-gateway `ug mcp-proxy`)
transport: http
version_observed: n/a (hosted, no local version)
verified: 2026-09-27
registered: true
pinned: false
---

# databricks-mcp — setup

Databricks' managed MCP servers, published as **MCP services** in the workspace's `system.ai`
Unity Catalog schema. Every one of them has the same endpoint shape and the same authentication,
so this one page covers the whole family for **Claude Code** and **GitHub Copilot CLI**.

Verified against Databricks' [managed MCP servers page](https://docs.databricks.com/aws/en/generative-ai/mcp/managed-mcp),
[Genie One page](https://docs.databricks.com/aws/en/agents/mcp-tools/genie-mcp) and
[MCP Services page](https://docs.databricks.com/aws/en/agents/mcp-tools/mcp-services), Claude
Code's [MCP docs](https://code.claude.com/docs/en/mcp), `copilot mcp add --help` (Copilot CLI
1.0.88), and the [Unity Gateway README](https://github.com/databricks/unity-gateway), on 27
September 2026. The service list and tool lists below were read from this workspace that day.
Databricks labels managed MCP servers **Public Preview**.

**Observed on macos-workstation, 2026-09-27:** all four servers showed `✔ Connected` in Claude Code.
A Copilot CLI session listed every tool from all four, and its `databricks-dbsql` `execute_sql`
call ran `SELECT 1 AS ok` and returned `ok = 1`.

## The servers

`system.ai` in this workspace holds 11 services, listed with
`databricks api get '/api/2.1/unity-catalog/mcp-services?parent=schemas/system.ai&view=BASIC'`. They
fall into two groups, and **this workbench registers group A only**.

**Group A: backed by Databricks itself** (`"config": {"internal": {}}`). The Databricks CLI token is
all they need.

| Service | Server name | Tools | Use it for |
| --- | --- | --- | --- |
| `genie_one_mcp` | `databricks-genie_one_mcp` | `genie_ask`, `genie_poll_response`, `genie_get_query_result`, `genie_cancel_response` | Natural-language questions over Unity Catalog data |
| `dbsql` | `databricks-dbsql` | `execute_sql`, `poll_sql_result` | Running SQL you wrote against Unity Catalog. **Can write** (see [Traps](#traps)). |
| `web_search` | `databricks-web_search` | `web_search` | Public web search through Databricks |
| `sandbox` | `databricks-sandbox` | `run_code` | Running Python, SQL or `sh` on Databricks compute |

**Group B: backed by a SaaS app, not registered here.** `github`, `slack`, `atlassian`, `gmail`,
`google_calendar`, `google_drive` and `microsoft_365` each forward to a SaaS app under your own
account. Before their tools work, each needs a one-time per-user sign-in to that app. That sign-in
re-runs your CLI login with an extra `--resource` option, and its effect on the profile's token for
other uses hasn't been tested. They are left out until it has.

## Parameters

| Variable | What it is | Where to get it | This workbench |
| --- | --- | --- | --- |
| `DBX_PROFILE` | Databricks CLI profile that holds your login | `databricks auth profiles` → `Name` | `dbc-5223e681-f77d` |
| `DBX_HOST` | Workspace URL, no trailing slash | `databricks auth describe -p "$DBX_PROFILE"` → `host` | `https://dbc-5223e681-f77d.cloud.databricks.com` |
| `DBX_WORKSPACE_ID` | Numeric workspace ID, sent as `?o=` | `databricks auth describe -p "$DBX_PROFILE"` → `workspace_id` | `4376027739142899` |
| `SERVICE` | One of the four group A services | the table above | — |

Server names are always `databricks-<service>`, so a tool shows up as
`mcp__databricks-dbsql__execute_sql` in Claude Code.

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

**The script prints the commands and runs none of them.** Review them, then run them yourself:

```sh
python workstation/scripts/databricks_mcp.py --profile "$DBX_PROFILE"            # all 4, both clients
python workstation/scripts/databricks_mcp.py --profile "$DBX_PROFILE" --client copilot --service dbsql
python workstation/scripts/databricks_mcp.py --profile "$DBX_PROFILE" --remove   # the matching removals
```

The script reads the host and workspace ID with `databricks auth describe` unless you pass `--host` and
`--workspace-id`. `--claude-scope user` registers the Claude servers for every project, not just this
one. On macOS outside the venv, the command is `python3`
([`../../scripts/README.md`](../../scripts/README.md)).

To pipe the output straight to a shell once you've read it:
`python workstation/scripts/databricks_mcp.py --profile "$DBX_PROFILE" | sh`.

For one service, the Claude line is:

```sh
claude mcp add-json -s local databricks-dbsql '{"type": "http", "url": "https://<host>/ai-gateway/mcp-services/system.ai.dbsql?o=<id>", "headersHelper": "databricks auth token -p <profile> | jq -c …"}'
```

The Copilot line is `copilot mcp add databricks-dbsql`, followed by `--` and the bridge command. It
writes this entry to `~/.copilot/mcp-config.json`:

```json
{
  "databricks-dbsql": {
    "tools": ["*"],
    "type": "local",
    "command": "ug",
    "args": ["mcp-proxy", "--url", "https://<host>/ai-gateway/mcp-services/system.ai.dbsql?o=<id>",
             "--host", "https://<host>", "--profile", "<profile>"]
  }
}
```

### Confirm

| Client | Command | Expect |
| --- | --- | --- |
| Claude Code | `claude mcp get databricks-<service>` | `Status: ✔ Connected` |
| Copilot CLI | `copilot mcp get databricks-<service>` | `Status: Enabled`, `Command: ug mcp-proxy …` |

`copilot mcp get` reports the config only; it doesn't connect. Proof that the connection works comes
from the tools appearing in a Copilot session. Either way, **restart the client** (or reconnect with
`/mcp` in Claude Code): a running session keeps the servers it loaded at startup.

To test the Copilot bridge without Copilot, pipe an MCP `initialize` into it. It should print a reply
whose `serverInfo.name` is the service:

```sh
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}' \
  | ug mcp-proxy --url "$DBX_HOST/ai-gateway/mcp-services/system.ai.dbsql?o=$DBX_WORKSPACE_ID" --profile "$DBX_PROFILE"
```

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

- **`databricks-dbsql` can change data.** `execute_sql` "supports SELECT and, unless disabled by
  policy, writes (INSERT/UPDATE/CREATE/etc.)". The limit is whatever your Unity Catalog grants allow,
  so review every statement before approving the tool call. `databricks-sandbox` runs arbitrary code
  on Databricks compute, so the same applies.
- **A Claude `headersHelper` doesn't run until the folder is trusted.** That applies to local scope
  too. In a folder you haven't accepted the trust dialog for, `claude mcp get` prints
  `headersHelper not run — this workspace has no persisted trust` and then `✘ Failed to connect`.
  Open Claude Code there once and accept the dialog.
- **`401 … Credential was not sent or was of an unsupported type`** means a static
  `headers.Authorization` holds something that isn't a valid token. On this machine it was the
  literal `Bearer ~`. Remove the entry and register it again from the script's output.
- **Everything fails after the CLI login expires.** `databricks auth profiles` then shows
  `Valid NO`. Run `databricks auth login -p "$DBX_PROFILE"` again.
- **A connected server can still have a tool that doesn't work in your workspace.** In this
  workspace, `databricks-web_search` connects and lists `web_search`, but calling it returns
  "Web search is unavailable in this workspace/region". That is a workspace or region property, not a
  setup fault, so don't re-register it. Ask a workspace admin whether web search can be enabled.
- **Keep the `?o=<workspace-id>` query string.** Every endpoint was verified with it, and the form
  without it hasn't been tested here.
- **Never commit a token**, in `.mcp.json` or anywhere else. Neither route needs one written down.

Docs: [Managed MCP servers](https://docs.databricks.com/aws/en/generative-ai/mcp/managed-mcp) ·
[Genie One](https://docs.databricks.com/aws/en/agents/mcp-tools/genie-mcp) ·
[MCP Services](https://docs.databricks.com/aws/en/agents/mcp-tools/mcp-services) ·
[Claude Code `headersHelper`](https://code.claude.com/docs/en/mcp) ·
[Copilot CLI MCP servers](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers) ·
full page ingest: [reference.md](reference.md)
