---
server: ado-remote-mcp
package: none — hosted endpoint
transport: http
version_observed: n/a (hosted, no local version)
verified: 2026-09-23
registered: false
pinned: n/a
---

# ado-remote-mcp — setup

Microsoft's hosted Azure DevOps MCP Server (`microsoft/azure-devops-mcp`), the **remote**
variant — no local install, streamable HTTP transport, endpoint
`https://mcp.dev.azure.com/{organization}`. This workbench's org: `euemadev`.

Verified directly against [Microsoft's own README](https://github.com/microsoft/azure-devops-mcp)
and the [remote-server docs page](https://learn.microsoft.com/en-us/azure/devops/mcp-server/remote-mcp-server)
it links to (23 September 2026) — not guessed.

> **Not yet registered.** The catalog entry in [`../.mcp.json`](../.mcp.json) is correct,
> but nobody has run the commands below or completed Claude Code's app registration.
> Until `claude mcp list` / `copilot mcp list` confirms a connection, treat the tools as
> unavailable.

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
copilot mcp add --transport http ado-remote-mcp https://mcp.dev.azure.com/euemadev
```

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
claude mcp add --transport http -s project ado-remote-mcp https://mcp.dev.azure.com/euemadev --client-id {client-id} --callback-port 3118
```

`-s project` writes the same tracked `.mcp.json` the catalog generates, with one extra
field Claude needs and Copilot doesn't:

```json
{
  "mcpServers": {
    "ado-remote-mcp": {
      "type": "http",
      "url": "https://mcp.dev.azure.com/euemadev",
      "oauth": {
        "clientId": "{client-id}",
        "callbackPort": 3118
      }
    }
  }
}
```

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

Use this when you specifically need a PAT or a fixed default project/team — the two
things the remote server cannot do. It's the `stdio` npm package, `@azure-devops/mcp`.

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
