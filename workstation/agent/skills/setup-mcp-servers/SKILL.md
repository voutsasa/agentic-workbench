---
name: setup-mcp-servers
description: Set up documented workstation MCP servers safely: detect client and tool readiness, ask for non-secret route choices, generate user-run commands, and verify read-only state. Use when setting up draw.io, Azure DevOps, or Databricks MCP servers.
---

# Set up MCP servers

This skill sets up the documented workstation MCP routes: `drawio-mcp`, `ado-remote-mcp`, and
Databricks managed MCP services. It reads the workbench root from `~/.claude/machine.md` and never
assumes the current repository is the workbench.

## Never

- Ask for, display, store, or place a PAT, OAuth client secret, access token, or credential in a
  command.
- Run `mcp add`, `mcp remove`, `link_config.py --apply`, an installation, or a sign-in command.
- Write a client configuration, `.mcp.json`, settings file, or machine note.
- Use `ug configure`, `ug claude`, or `ug mcp add --agents ...`; those can redirect model traffic.

The user runs every registration and authentication command. This skill only discovers state and
hands over commands from the recorded setup routes.

## 1. Discover

Run the skill's deterministic discovery script without a Databricks profile first:

```sh
<python> <skill>/scripts/discover.py
```

It reports the workbench root, catalog/project server names, available clients, and required tools.
Show the JSON result. A missing client or tool is a blocker: give the user the recorded install route
from `workstation/cli/` and stop for that server.

Only after the user selects an existing Databricks CLI profile, run:

```sh
<python> <skill>/scripts/discover.py --databricks-profile <profile>
```

That makes one read-only Unity Catalog query and returns only currently internal `system.ai` services.
If it reports `unavailable`, show its detail and do not generate registration commands.

## 2. Ask

Ask only questions that apply, in structured form when available. Never request secret values.

| Server | Ask |
|---|---|
| draw.io | Which available client(s); shared project catalog or personal user scope; whether opening URL-encoded diagrams in a browser is acceptable. |
| Azure DevOps | Remote Entra OAuth or local server; organization; available client(s); read-only/toolset restriction; and, for Claude remote OAuth, whether a tenant app registration and client ID already exist. For local routes ask only the auth method and optional default project/team, never the credential. |
| Databricks | Available client(s); existing CLI profile; discovered internal service(s); and Claude local or user scope. |

Read the selected server's `workstation/mcp/<server>/setup.md` before deciding a route.

## 3. Hand over commands

Give exact commands from the setup guide or `workstation/scripts/databricks_mcp.py`, with the
user-supplied non-secret values substituted. State every file the command changes and what it cannot
prove.

- Draw.io shared route: give the user the `link_config.py --mcp --apply` command; personal route:
  give the appropriate `claude mcp add` or `copilot mcp add` command.
- ADO remote: explain Entra browser sign-in. For Claude, stop until the tenant app registration exists;
  client ID is not a secret but the user chooses user versus project scope. For local ADO, hand over
  the environment-variable route without placing a PAT in the command.
- Databricks: run the generator only after discovery reports services available. It prints commands
  but registers nothing. The user reviews and runs one selected line.

## 4. Verify

After the user reports registration, run only read-only configuration checks:

| Server | Check |
|---|---|
| draw.io / ADO | `claude mcp list` or `copilot mcp list`, as applicable |
| Databricks | `copilot mcp get databricks-<service>` or `claude mcp get databricks-<service>` |

Configuration status alone is not a connection proof. Ask the user to restart the client and invoke
one approved read-only tool; record a failed or absent response as unverified rather than retrying
registration.
