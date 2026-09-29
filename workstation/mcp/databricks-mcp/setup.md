---
server: databricks-mcp
package: none — hosted endpoints (Copilot CLI bridge: unity-gateway `ug mcp-proxy`)
transport: http
version_observed: n/a (hosted, no local version)
verified: 2026-09-29
pinned: false
---

# databricks-mcp — setup

**This guide is for Azure Databricks.** Every Databricks page it cites is the Azure edition on
Microsoft Learn, and the workspace it assumes is an Azure Databricks workspace.

Azure Databricks' managed MCP servers come in two shapes: **MCP Services** in the workspace's
`system.ai` Unity Catalog schema, reached through Unity Gateway, and **managed servers** under
`/api/2.0/mcp/`. This guide registers the first kind for **Claude Code** and **GitHub Copilot CLI**.
Which services a workspace offers varies, so commands are generated from the live catalog rather than
copied from a fixed list.

Verified against Microsoft Learn's Azure Databricks pages — [managed MCP servers](https://learn.microsoft.com/en-us/azure/databricks/agents/mcp-tools/managed-mcp),
[Databricks-provided MCP Services](https://learn.microsoft.com/en-us/azure/databricks/agents/mcp-tools/built-in-mcp-services),
[Genie One](https://learn.microsoft.com/en-us/azure/databricks/agents/mcp-tools/genie-mcp),
[Databricks SQL](https://learn.microsoft.com/en-us/azure/databricks/agents/mcp-tools/databricks-sql),
[Genie Agent](https://learn.microsoft.com/en-us/azure/databricks/agents/mcp-tools/genie-agent),
[AI Search](https://learn.microsoft.com/en-us/azure/databricks/agents/mcp-tools/ai-search) and
[Unity Catalog functions](https://learn.microsoft.com/en-us/azure/databricks/agents/mcp-tools/uc-functions),
dated 11 and 21 September 2026 — and Claude Code's [MCP docs](https://code.claude.com/docs/en/mcp),
`copilot mcp add --help`, and the [Unity Gateway README](https://github.com/databricks/unity-gateway),
on 29 September 2026.

## The server family

### MCP Services in `system.ai` — what the generator registers

Endpoint `$DBX_HOST/ai-gateway/mcp-services/system.ai.<service>`, OAuth scope `ai-gateway`. Each
service is a Unity Catalog securable with a built-in service policy; account users hold `EXECUTE` on
`system.ai` by default.

**Workspace tools** — authenticated by the Databricks CLI token alone:

| Service | Status | Capability | Tools | Writes |
| --- | --- | --- | --- | --- |
| `genie_one_mcp` | GA | Natural-language analytics across the workspace: Genie searches the data, writes and runs SQL, and answers grounded in Genie Ontology, with deep links to its sources | `genie_ask`, `genie_poll_response`, `genie_get_query_result`, `genie_cancel_response`; `view_ask` instead of `genie_ask` on MCP Apps clients | Queries only; Unity Catalog permissions apply to every request |
| `dbsql` | Beta | Runs SQL on a SQL warehouse with the caller's Unity Catalog and warehouse permissions; queries run asynchronously | `execute_sql` (the name in Microsoft's example) | **Reads and writes by default.** Read-only once `disallow_writes` is `true` in the `system.ai.dbsql_policy` policy |
| `sandbox` | Beta | Runs Python, SQL or shell code in an isolated environment | not listed | No network egress |

**Connected applications** — call a third-party service and need their own per-user sign-in, so the
generator excludes them: `slack`, `github`, `atlassian` (Jira and Confluence), `google_drive`,
`google_calendar`, `gmail`, `microsoft_365` (SharePoint, Outlook and Teams). Google and Microsoft 365
each need a one-time OAuth login in Catalog Explorer before the first call.

### Managed servers under `/api/2.0/mcp/` — Public Preview, generated on request

Endpoint `$DBX_HOST/api/2.0/mcp/<path>`. Each needs a resource path that only you know, so the
generator prints them only when you name them:
[Register an `/api/2.0/mcp/` server](#register-an-api20mcp-server).

| Server | Path | OAuth scope | Capability | Writes |
| --- | --- | --- | --- | --- |
| Genie Agent | `genie/{genie_space_id}` | `genie` | Natural-language questions over one Genie Agent — up to 25 Unity Catalog tables | Read-only; no conversation history between calls |
| AI Search | `ai-search/{catalog}/{schema}/{index_name}` | `ai-search` | Semantic search over an AI Search (formerly Vector Search) index; needs Databricks managed embeddings. One tool per index, named `CATALOG__SCHEMA__INDEX_NAME` | Queries only |
| Databricks SQL | `sql` | `sql` | Same as `dbsql` above; Microsoft recommends the `system.ai.dbsql` service for its grants, policies and audit log | Reads and writes |
| Unity Catalog functions | `functions/{catalog}/{schema}/{function_name}` | `unity-catalog` | Registered Python and SQL functions as tools, plus the `system.ai` functions such as the `python_exec` code interpreter | Whatever the function does |

The Beta Genie endpoint `/api/2.0/mcp/genie`, with no space ID, is deprecated and is sunset on
31 October 2026; use `system.ai.genie_one_mcp`.

### How the generator chooses

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

## Register an `/api/2.0/mcp/` server

The generator prints the same two entry shapes for these, with the resource path you name. Asking
only for these servers skips the catalog query:

```sh
python workstation/scripts/databricks_mcp.py --profile "$DBX_PROFILE" --genie-space <genie_space_id>
python workstation/scripts/databricks_mcp.py --profile "$DBX_PROFILE" --ai-search <catalog>.<schema>.<index_name>
python workstation/scripts/databricks_mcp.py --profile "$DBX_PROFILE" --ai-search <catalog>.<schema>   # every index in it
python workstation/scripts/databricks_mcp.py --profile "$DBX_PROFILE" --remove --genie-space <genie_space_id>
```

| Flag | Server name | Where the ID comes from |
| --- | --- | --- |
| `--genie-space <id>` | `databricks-genie-<id>` | The Genie Agent's page in the workspace; the agent must be shared with you |
| `--ai-search <c>.<s>.<i>` | `databricks-ai-search-<c>-<s>-<i>` | Catalog Explorer → the index |
| `--ai-search <c>.<s>` | `databricks-ai-search-<c>-<s>` | The form Microsoft's own example uses |

Both flags repeat and combine with `--service` and `--client`. IDs are restricted to letters, digits
and `_` (the space ID to letters and digits), because they end up in a shell command. Confirm as in
[Confirm](#confirm).

**Not yet observed here:** a connection to any `/api/2.0/mcp/` endpoint. Microsoft's URL patterns
carry no `?o=` query string, so none is added; and the CLI login's default `all-apis` scope has been
seen to work only for the `system.ai` services. A `401`/`403` on first connect points at the scope
first — the servers want `genie`, `ai-search` and `sql`.

## Databricks SQL — guidance, not registered by default

`$DBX_HOST/api/2.0/mcp/sql`, OAuth scope `sql`, one tool (`execute_sql` in Microsoft's example).
It runs whatever SQL the agent writes, asynchronously, with the caller's Unity Catalog and warehouse
permissions.

**It reads and writes, and no service policy applies to it.** The read-only switch Microsoft
documents — `disallow_writes` in `system.ai.dbsql_policy` — belongs to the `system.ai.dbsql` MCP
Service, not to this endpoint, and tool selection cannot help when the server has one tool. What an
agent can change through it is exactly what the signed-in identity can change.

Before registering it:

1. **Decide which identity it runs as.** Your own login gives the agent every write privilege you
   hold. For read-only use, register it under a profile whose identity holds only `USE CATALOG`,
   `USE SCHEMA` and `SELECT` on the data in question — a separate Databricks CLI profile, for
   example one logged in as a service principal granted nothing more.
2. **Prefer `system.ai.dbsql` where the workspace offers it.** Microsoft recommends it for its grants,
   policies, audit log and usage tracking, and it is the only route with a documented read-only
   switch. Setting that switch is a workspace-wide change: service policies are Beta, and an account
   admin must first turn on the **Unity Gateway** beta features on the account console **Previews**
   page.
3. **Pin the warehouse if cost or isolation matters.** The server otherwise picks one; agent code can
   pass `warehouse_id` as a `_meta` parameter, but neither client's registration can.

To register it once those are settled, run the generator with `--sql` and `--profile` set to the
identity chosen in step 1. `--sql` is never implied, and the generator warns on stderr that the
server writes:

```sh
python workstation/scripts/databricks_mcp.py --profile <read-only-profile> --sql
```

Databricks SQL is hosted by Azure Databricks, like every server in this guide: there is nothing to
install locally beyond the Databricks CLI, `jq` and, for Copilot, `ug`.

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
  been checked. `dbsql` is the known case: it writes unless its policy says otherwise.
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

Docs (Azure Databricks): [Managed MCP servers](https://learn.microsoft.com/en-us/azure/databricks/agents/mcp-tools/managed-mcp) ·
[Databricks-provided MCP Services](https://learn.microsoft.com/en-us/azure/databricks/agents/mcp-tools/built-in-mcp-services) ·
[Genie One](https://learn.microsoft.com/en-us/azure/databricks/agents/mcp-tools/genie-mcp) ·
[Claude Code `headersHelper`](https://code.claude.com/docs/en/mcp) ·
[Copilot CLI MCP servers](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers) ·
full page ingest: [reference.md](reference.md)
