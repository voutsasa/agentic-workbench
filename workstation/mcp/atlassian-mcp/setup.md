---
server: atlassian-mcp
package: none — hosted endpoint
transport: http
version_observed: v2
verified: 2026-10-13
pinned: true
author: Achilleas Voutsas
version: 0.3.0
---

# atlassian-mcp — setup

Atlassian's hosted v2 MCP server provides OAuth 2.1 access to the signed-in user's connected
Atlassian products, including **Confluence**, Jira, Jira Service Management, Bitbucket, Projects,
Goals, and Loom. It is remote HTTP transport: there is no local package to install. Source:
[`reference.md`](reference.md), ingested from Atlassian's setup guide on 2026-10-13.

> **Intended setup, not observed.** This guide records the supported registration route. It does not
> mean the server is registered, authenticated, or connected on this machine.

## Permission boundary and cost

This is **not a Confluence-only server**. It exposes whichever connected Atlassian products the
signed-in user can access, and it can create or update pages and work items. Atlassian's published
setup does not document a Confluence-only tool filter. Use an account with the least necessary
permissions, review requested writes before confirming them, and monitor the Atlassian audit log.

Rovo credits are consumed per tool call. Larger context retrievals and more complex requests consume
more credits from the organization's shared Rovo allowance.

| Aspect | Value |
|---|---|
| Endpoint | `https://mcp.atlassian.com/v2/mcp` |
| Transport | Streamable HTTP |
| Authentication | Browser-based OAuth 2.1, using your existing Atlassian identity |
| Version | v2, selected by the endpoint path |
| Configuration in this repo | [`../.mcp.json`](../.mcp.json) catalog, merged into the tracked root `.mcp.json` |

## First-time setup information

Before starting authentication, ask the user for:

- the Atlassian organization or Cloud site they intend to access;
- the user name or email of the identity that will authorize the MCP server.

**Never ask the user to paste an API key into chat, a command, this repository, or the tracked root
`.mcp.json`.** OAuth is the recommended route. If an organization administrator has enabled
API-token authentication and the user deliberately selects it, direct them to Atlassian's
[API-token configuration guide](https://support.atlassian.com/atlassian-ai-gateway/docs/configure-authentication-via-api-token/).
The user must follow that guide themselves and use a secure, user-managed MCP configuration; this
workbench does not record or distribute the key.

## Shared project registration — recommended

The catalog has the vendor's generic endpoint, so the same project-scoped configuration serves both
Claude Code and GitHub Copilot CLI. **Run these yourself; they are not run by this guide.**

```powershell
.\.venv\Scripts\python.exe workstation\scripts\link_config.py --mcp
.\.venv\Scripts\python.exe workstation\scripts\link_config.py --mcp --apply
```

The first command only reports the catalog state. The second adds the missing `atlassian-mcp` entry to
this repository's tracked `.mcp.json`; it does not alter an existing diverged entry. Both clients read
that file from this workspace. It contains no credential.

### Claude Code

Open Claude Code in this repository, run `/mcp`, select `atlassian-mcp`, and complete the browser
sign-in. Verify configuration with:

```powershell
claude mcp get atlassian-mcp
```

### GitHub Copilot CLI

Start a new Copilot CLI session in this repository. Confirm the workspace configuration:

```powershell
copilot mcp get atlassian-mcp
```

Then make a read-only request such as *“Search Confluence for `<page title>` and summarize the
results.”* Complete the browser sign-in when prompted. `copilot mcp get` proves only that the
configuration is enabled; a successful read proves the OAuth connection and permissions.

## Personal registration — alternative

Use one of these **instead of** the shared project catalog if the server should apply outside this
repository. Each command writes a user-specific, untracked configuration; neither command puts a
credential in the configuration.

```powershell
claude mcp add --transport http -s user atlassian-mcp https://mcp.atlassian.com/v2/mcp
```

```powershell
copilot mcp add --transport http atlassian-mcp https://mcp.atlassian.com/v2/mcp
```

Claude writes `~/.claude.json`; Copilot CLI writes `~/.copilot/mcp-config.json`. Open a new client
session and trigger the OAuth flow as above.

## Traps

- Use the **v2** endpoint above. Atlassian says existing v1 use will begin exposing v2 tools on
  2027-03-01; incompatible clients may need their cached client IDs or `.well-known` credentials
  cleared.
- Do not add a static `Authorization` header or an API token unless an Atlassian administrator has
  explicitly chosen that separate authentication route. The documented default is interactive OAuth.
- A configured server is not an authenticated connection. Restart the client and complete one
  read-only Confluence request before relying on it.
- Authentication respects existing Atlassian permissions; adding this server never grants Confluence
  access that the identity did not already have.

Docs: [Atlassian remote MCP server setup](https://support.atlassian.com/atlassian-ai-gateway/docs/get-started-with-the-atlassian-remote-mcp-server/) · full page ingest: [reference.md](reference.md)
