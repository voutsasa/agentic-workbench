---
server: ado-remote-mcp
package: none — hosted endpoint
transport: http
version_observed: n/a (hosted, no local version)
verified: 2026-09-28
pinned: false
author: Achilleas Voutsas
version: 0.3.0
---

# ado-remote-mcp — setup

Microsoft's hosted Azure DevOps MCP Server (`microsoft/azure-devops-mcp`), the **remote**
variant — no local install, streamable HTTP transport, endpoint
`https://mcp.dev.azure.com/{organization}`. This workbench's org: `euemadev`.

Verified directly against [Microsoft's own README](https://github.com/microsoft/azure-devops-mcp)
and the [remote-server docs page](https://learn.microsoft.com/en-us/azure/devops/mcp-server/remote-mcp-server)
it links to (23 September 2026) — not guessed.

> **Whether this is registered on your machine is machine state, not a fact this file can carry** — see
> [`../../machines/`](../../machines/). The catalog entry in [`../.mcp.json`](../.mcp.json) is correct
> either way. Confirm with `claude mcp list` / `copilot mcp list` before assuming a connection.

## Remote first — but read the auth asymmetry before picking a client

The remote server **only supports Microsoft Entra ID (OAuth). It has no PAT option.**
Permissions come entirely from the signed-in identity's actual Azure DevOps access — a
project membership, not an MCP setting. If you need a PAT or a fixed default project,
skip to [Local server](#local-server--pat-and-project-defaults) below; that is the
local `npx @azure-devops/mcp` variant, and it is the *only* one that supports either.

| Client | Remote server needs |
| --- | --- |
| **GitHub Copilot CLI** | Nothing extra — it's a natively supported environment. |
| **Claude Code** | A one-time, **org-wide** Microsoft Entra app registration (below). Cursor needs the same; Claude Desktop and Codex can't use the remote server at all — Entra doesn't support the dynamic client registration they require. |

**Why Claude's plain catalog entry fails.** When only the shared HTTP entry is present, Claude Code
attempts dynamic client registration. Azure DevOps MCP rejects it with *"Incompatible auth server:
does not support dynamic client registration."* A tenant-specific client ID is therefore mandatory
for Claude Code, not an optional configuration detail. The shared catalog cannot carry it because it
is tenant-specific.

**Choose the local server when that Entra registration is unavailable or when a PAT is required.**
The remote server supports Entra OAuth only; the local `@azure-devops/mcp` server is the supported
alternative for PAT authentication and a default project or team. Its setup is in
[Local server — PAT and project defaults](#local-server--pat-and-project-defaults).

**Why Copilot needs nothing and Claude does.** GitHub Copilot CLI is on Microsoft's own
[supported-environments list](https://learn.microsoft.com/en-us/azure/devops/mcp-server/remote-mcp-server#supported-environments)
alongside Visual Studio, Microsoft Foundry, and Copilot Studio — first-party Microsoft products
Entra ID pre-registers and pre-consents in every tenant. Claude Code is third-party from Entra's
side: no tenant has it pre-registered, so each tenant must create its own app registration before
OAuth can start at all. This is a Microsoft-vs-third-party distinction, not a gap either this repo
or Claude's config can close.

### GitHub Copilot CLI

The shared catalog (this repo's `.mcp.json`, generated from
[`../.mcp.json`](../.mcp.json) by `link_config.py --mcp --apply` — see
[`../README.md`](../README.md)) already carries the plain, Entra-only block. Copilot CLI
reads it at workspace scope with no further setup:

```json
{
  "mcpServers": {
    "ado-remote-mcp": {
      "type": "http",
      "url": "https://mcp.dev.azure.com/euemadev",
      "headers": {
        "X-MCP-Readonly": "true"
      }
    }
  }
}
```

Confirm with `copilot mcp list` after opening this repo. First use prompts a Microsoft
Entra sign-in in the browser.

For a personal, every-repo registration instead of the shared file:

```
copilot mcp add --transport http --header "X-MCP-Readonly: true" ado-remote-mcp https://mcp.dev.azure.com/euemadev
```

Keep the `X-MCP-Readonly` header in every route: it restricts the server to its read-only tools
(`reference.md` § *Read-only tools*), and the shared catalog sets it.

### Claude Code

**Needs an app registration your tenant may not have yet — this is not a per-engineer
self-serve step**, and the admin-consent part may require a tenant administrator.

1. Confirm the **Azure DevOps MCP** enterprise application is already provisioned in
   your Entra tenant (search the app ID `2a72489c-aab2-4b65-b93a-a91edccf33b8` in the
   Microsoft Entra admin center). If it isn't, that is a tenant-level gap outside this
   repo's scope.
2. Create an **app registration**: Authentication (Preview) → Add redirect URI → Mobile
   and desktop applications → `http://localhost:3118/callback`. On the Settings tab,
   enable **Allow public client flows**.
3. API permissions → Add a permission → APIs my organization uses → search **Azure
   DevOps MCP** (or the app ID above) → select the delegated permissions needed → **Grant
   admin consent** (tenant admin, if you aren't one).
4. Copy the **Application (client) ID**.

Then, replacing `{client-id}`:

```
claude mcp add --transport http -s project ado-remote-mcp https://mcp.dev.azure.com/euemadev --header "X-MCP-Readonly: true" --client-id {client-id} --callback-port 3118
```

`-s project` writes the same tracked `.mcp.json` the catalog generates, with one extra
field Claude needs and Copilot doesn't:

```json
{
  "mcpServers": {
    "ado-remote-mcp": {
      "type": "http",
      "url": "https://mcp.dev.azure.com/euemadev",
      "headers": {
        "X-MCP-Readonly": "true"
      },
      "oauth": {
        "clientId": "{client-id}",
        "callbackPort": 3118
      }
    }
  }
}
```

**Scope choice — personal vs. shared.** `-s project` above commits your client ID into the tracked
`.mcp.json`, visible to every engineer who clones this repo. `-s user` instead writes to
`~/.claude.json`, staying personal and untracked — swap `-s project` for `-s user` in the command if
you don't want to commit it yet. The client ID itself isn't a secret, so committing it is safe once
your tenant's app registration exists; making it the shared default for every EMA engineer using this
repo is a deliberate call for whoever registers it first, not a side effect of getting your own
connection working.

Adding the `oauth` block doesn't affect Copilot CLI reading the same file: verified by adding a
placeholder `oauth` block to `.mcp.json` and confirming `copilot mcp list` still shows
`ado-remote-mcp (http)` unchanged, then reverting it (2026-09-28).

**The shared catalog deliberately omits `oauth.clientId`.** It only works once the app
registration above exists, it's specific to your tenant, and there's no way to verify
one from this repo. Add it to your own `.mcp.json` once you have a real client ID —
`link_config.py --mcp` will then report the entry `diverged` against the catalog, which
is correct: the catalog can't run without your tenant's client ID, so the two versions
are expected to differ. Start Claude, run `/mcp`, and follow the browser sign-in.

## Scoping the tools that appear

HTTP headers, not URL parameters — add them under `headers` in either client's config.
Don't combine `X-MCP-Toolsets` and `X-MCP-Tools`.

| Header | Effect |
| --- | --- |
| `X-MCP-Readonly: "true"` | Read-only tools only. **On by default in the shared catalog.** |
| `X-MCP-Toolsets: "repos,wiki,wit"` | Only these tool groups. Values: `all` (default), `repos`, `advsec`, `wit`, `pipelines`, `wiki`, `work`, `testplan`, `elm`. |
| `X-MCP-Tools: "core_list_projects, wit_work_item"` | Only these named tools. |
| `X-MCP-Insiders: "true"` | Early access to new/changed tools. |

There is **no header that restricts which ADO *project* is visible** — that's governed
entirely by the signed-in identity's real Azure DevOps permissions, remote or local.

## Local server — PAT and project defaults

Use this when you specifically need a PAT, a fixed default project/team, or cannot obtain the
tenant-level Claude Code app registration required by the remote server. It's the `stdio` npm package,
`@azure-devops/mcp`.

Authentication methods (`--authentication <value>` / `-a <value>`, default `interactive`):

| Method | Value | Requires |
| --- | --- | --- |
| Interactive | `interactive` | Browser Microsoft sign-in |
| Azure CLI | `azcli` | `az login` |
| Azure credential chain | `env` | `DefaultAzureCredential` setup |
| Bearer token | `envvar` | `ADO_MCP_AUTH_TOKEN` env var |
| **Personal Access Token** | `pat` | `PERSONAL_ACCESS_TOKEN` env var — base64 of `<email>:<pat>` |

```bash
export PERSONAL_ACCESS_TOKEN="$(printf '%s' '<email>:<pat>' | base64)"
```

> Do not commit a PAT to any MCP config file. Set it as an environment variable or in a
> secrets manager, never in `.mcp.json`.

Claude Code:

```
claude mcp add --transport stdio ado-local-mcp -e PERSONAL_ACCESS_TOKEN=<base64> -- npx -y @azure-devops/mcp euemadev --authentication pat
```

Copilot CLI (edit `~/.copilot/mcp-config.json`, or `copilot mcp add` with `--env`):

```
copilot mcp add ado-local-mcp --env PERSONAL_ACCESS_TOKEN=<base64> -- npx -y @azure-devops/mcp euemadev --authentication pat
```

**Project/team default, not a restriction.** These only pre-fill the values so tools
skip a selection prompt — they do not limit what the authenticated identity can reach:

```bash
npx -y @azure-devops/mcp euemadev --authentication azcli
```
```
env: { "ado_mcp_project": "YourProject", "ado_mcp_team": "YourTeam" }
```

**Domains** narrow which local tools load (`-d core work work-items`, etc.) — the local
equivalent of the remote server's `X-MCP-Toolsets`. Always include `core`.

## Traps

- **`.vscode/mcp.json` is VS Code's own file and Copilot CLI does not read it.** For this
  repo, the tracked root `.mcp.json` (generated from the catalog) is the route for both
  Claude Code and Copilot CLI — don't confuse the two.
- **Claude Desktop and Codex cannot use the remote server at all.** Microsoft Entra ID
  doesn't support the dynamic OAuth client registration these clients require. Use the
  local server with them.
- **The remote server's `X-MCP-Toolsets`/`X-MCP-Tools` restrict *tool categories*, not
  *projects*.** Someone with access to five ADO projects still sees all five through
  either server; there is no per-project allowlist on either side.
- **A missing organization segment in the URL is legal** (`https://mcp.dev.azure.com/`
  with no name) but then every tool call must name the organization explicitly. This
  workbench's catalog always includes `euemadev`, so this shouldn't come up here.
- **Connection Refused** usually means a corporate proxy/firewall is blocking outbound
  HTTPS to `mcp.dev.azure.com` — ask whoever administers the network to allow-list it.

Docs: [azure-devops-mcp README](https://github.com/microsoft/azure-devops-mcp) ·
[remote server setup](https://learn.microsoft.com/en-us/azure/devops/mcp-server/remote-mcp-server) ·
full page ingest: [reference.md](reference.md)
