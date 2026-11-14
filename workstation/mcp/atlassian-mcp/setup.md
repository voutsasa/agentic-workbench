---
server: atlassian-mcp
package: none — hosted endpoint
transport: http
version_observed: v2
verified: 2026-10-13
pinned: true
author: Achilleas Voutsas
version: 0.4.1
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
| Configuration scope | **User**, per client — deliberately not in the [`../.mcp.json`](../.mcp.json) catalog |

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

## Workstation registration — user scope

Confluence is wanted in every Claude Code and Copilot CLI session on the machine, not only in this
repository, so the server is registered **once per client at user scope** and is deliberately absent
from the [`../.mcp.json`](../.mcp.json) catalog. `link_config.py --mcp` therefore does not list it.
**Run these yourself; they are not run by this guide.** The commands are the same on macOS (zsh) and
Windows (PowerShell), and neither puts a credential in the configuration.

| Client | Command | Writes |
|---|---|---|
| Claude Code | `claude mcp add --transport http -s user atlassian-mcp https://mcp.atlassian.com/v2/mcp` | `~/.claude.json` |
| GitHub Copilot CLI | `copilot mcp add --transport http atlassian-mcp https://mcp.atlassian.com/v2/mcp` | `~/.copilot/mcp-config.json` |

`copilot mcp add` has no scope flag: its `--help` says it adds the server "to the user configuration"
(Copilot CLI 1.0.88, 2026-10-13). Atlassian's own Claude Code command omits `-s user` and so
registers at local (this-project) scope; the flag is what makes it workstation-wide.

These files sit outside the repository, so the commands above are the only reproducibility record.

### Claude Code

Open a new Claude Code session, run `/mcp`, select `atlassian-mcp`, and complete the browser sign-in.
Verify configuration with:

```sh
claude mcp get atlassian-mcp
```

### GitHub Copilot CLI

Start a new Copilot CLI session and confirm the configuration:

```sh
copilot mcp get atlassian-mcp
```

Then make a read-only request such as *“Search Confluence for `<page title>` and summarize the
results.”* Complete the browser sign-in when prompted. `mcp get` proves only that the configuration is
enabled; a successful read proves the OAuth connection and permissions.

## Traps

- Do not also add `atlassian-mcp` to a repository's `.mcp.json`. A project-scope entry with the same
  name takes precedence over the user-scope one in Claude Code, leaving two copies to drift.
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
