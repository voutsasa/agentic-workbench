---
server: fabric-iq-mcp
package: none — hosted endpoint
transport: http
version_observed: n/a (hosted; tool contract pinned by header, Fabric.Routing.FabricIQ.V1)
verified: 2026-09-30
pinned: false
author: Achilleas Voutsas
version: 0.2.0
---

# fabric-iq-mcp — setup

**Remote, read-only.** Microsoft's hosted Fabric IQ MCP server gives an agent six tools over the Power
BI reports and semantic models the signed-in user can already see. It finds them, reads their
metadata, looks up values and runs DAX. There is nothing to install. Source:
[`reference.md`](reference.md), ingested from Microsoft Learn on 2026-09-30.

> **Intended setup, not observed.** Nothing below has been registered or connected on any machine
> yet. Confirm with `claude mcp list` / `copilot mcp list` and one tool call before relying on it.

## Endpoint and identity

| Aspect | Value |
| --- | --- |
| Endpoint | `https://fabriciq.svc.cloud.microsoft/v1/mcp/fabriciq` — with private links, `https://api.fabric.microsoft.com/v1/mcp/fabriciq` |
| Transport | Streamable HTTP |
| Identity | **You**, through delegated Entra OAuth. Service principals and app-only auth are not supported |
| Permissions | Delegated Power BI Service `Item.Read.All`, `Item.Execute.All`, `Dataset.Read.All`; no admin consent by default, but tenant policy can require it |
| Tool contract | Pinned with the header `X-Variants: Fabric.Routing.FabricIQ.V1`. The `v1` in the URL is the endpoint version, not the contract |
| Writes | None. RLS and OLS apply to every query |
| Prerequisites | A tenant whose home region supports all Fabric workloads; access to at least one report or semantic model |

## Register

The server name here is `fabric-iq-mcp`, matching this folder. Microsoft's example calls it
`FabricIQ`.

### Copilot CLI

Copilot CLI uses a preregistered Entra application, so no app registration is needed:

```sh
copilot mcp add --transport http --header "X-Variants: Fabric.Routing.FabricIQ.V1" --tools "*" fabric-iq-mcp https://fabriciq.svc.cloud.microsoft/v1/mcp/fabriciq
```

Writes `~/.copilot/mcp-config.json` (user config). Then start Copilot and run `/mcp show fabric-iq-mcp`;
the browser sign-in opens on first use.

### Claude Code

Claude Code has no preregistered Entra app for this server, and Entra does not support dynamic client
registration, which is the same failure `ado-remote-mcp` hits. **Stop until a single-tenant app
registration exists:**

1. Entra admin center → **App registrations** → **New registration** → *Accounts in this
   organizational directory only*.
2. **Authentication** → add a *Mobile and desktop applications* redirect URI,
   `http://localhost:3119/callback`. Any free port works if it matches `--callback-port` below.
3. **API permissions** → *APIs my organization uses* → **Power BI Service** → *Delegated*:
   `Item.Read.All`, `Item.Execute.All`, `Dataset.Read.All`.

Then, replacing `{client-id}`, which is not a secret:

```sh
claude mcp add --transport http -s user -H "X-Variants: Fabric.Routing.FabricIQ.V1" fabric-iq-mcp https://fabriciq.svc.cloud.microsoft/v1/mcp/fabriciq --client-id {client-id} --callback-port 3119
```

`-s user` writes `~/.claude.json`, personal and untracked. Use `-s project` only if every clone should
share the client ID through the tracked `.mcp.json`.

**Never add an `Authorization` header.** A static bearer token overrides the OAuth flow and stops
working when it expires.

## Confirm

| Step | Expect |
| --- | --- |
| `claude mcp get fabric-iq-mcp` / Copilot `/mcp show fabric-iq-mcp` | Connected, six tools listed |
| Ask: *Find the `<report name>` report in Microsoft Fabric.* | A `DiscoverArtifacts` call returns the item. This proves auth, permissions and tool execution |

Tools: `DiscoverArtifacts`, `ResolveFabricItem`, `GetReportMetadata`, `GetSemanticModelSchema`,
`ValueSearch`, `ExecuteQuery`. The runtime `tools/list` is authoritative.

## Traps

- **No natural-language answering tool.** The agent writes the DAX itself. Microsoft recommends
  pairing the server with the Fabric IQ skill from Skills for Fabric. That is a separate install, not
  recorded here.
- **Tools differ from the list above** → the `X-Variants` header is missing or wrong. Re-register with
  it.
- **A report isn't found** → paste its browser URL, not a Power BI *share* link.
- **Stale data** → the semantic model hasn't refreshed; the server reads what the model holds.
