---
server: powerbi-modeling-mcp
package: "@microsoft/powerbi-modeling-mcp (npm)"
transport: stdio
version_observed: "1.0.0 — npm registry dist-tag latest, 2026-09-30; not yet run on this machine"
verified: 2026-09-30
pinned: false
author: Achilleas Voutsas
version: 0.4.2
---

# powerbi-modeling-mcp — setup

**Local, and it writes.** Microsoft's Power BI Authoring MCP Server runs on this machine and gives
an agent 21 tools. They create, change and query semantic models: tables, measures,
relationships, RLS roles, translations, TMDL import and export, and DAX. It works against Power BI
Desktop, a Fabric workspace (over XMLA) or Power BI Project (PBIP) files. Source:
[`reference.md`](reference.md), the repo README ingested on 2026-09-30.

> **Intended setup, not observed.** Nothing below has been installed, registered or run on any
> machine yet. Mark the version and connection as observed only after the checks in *Confirm*.

**For a model in a Fabric workspace, Microsoft recommends the remote Power BI Authoring server
instead.** It needs no install and Microsoft updates it. This local server is for Power BI Desktop,
PBIP files, and working offline from the service.

## Install

Pick one route. The user runs every command.

| Route | For | What it needs |
| --- | --- | --- |
| **npx** (recommended here) | Claude Code and Copilot CLI | Node.js ≥ 18 (the package's `engines`). The package downloads on first launch; there is no separate install step |
| **VSIX download** | No Node, or a fixed build | A download from the VS Code Marketplace, unzipped to a folder of your choice |
| **VS Code extension** | GitHub Copilot Chat inside VS Code only | The *Power BI Authoring MCP* extension; neither CLI uses it |

**npx.** Check Node first: `node --version`, which prints `v<major>.<minor>.<patch>`. Node is already a
required workstation prerequisite (`workstation/dependencies.toml`); `workstation/scripts/status.py`
reports it. The package
is `@microsoft/powerbi-modeling-mcp`. Its registry entry points at
`github.com/microsoft/powerbi-modeling-mcp` and is published by Microsoft's release accounts. It
ships prebuilt binaries for `win32-x64`, `win32-arm64`, `darwin-arm64`, `linux-x64` and
`linux-arm64`. **There is no Intel-Mac (`darwin-x64`) binary.**

**VSIX download.** Replace `<version>` and `<platform>` (e.g. `1.0.0`, `win32-x64`):

```
https://marketplace.visualstudio.com/_apis/public/gallery/publishers/analysis-services/vsextensions/powerbi-modeling-mcp/<version>/vspackage?targetPlatform=<platform>
```

Rename the download to `.zip`, unzip it (e.g. to `C:\MCPServers\PowerBIAuthoringMCP`), and run
`extension\server\powerbi-modeling-mcp.exe` once. It prints the registration JSON. In the commands
below, replace `npx -y @microsoft/powerbi-modeling-mcp@latest` with that `.exe` path.

### Accept the EULA

Every tool call is blocked until the
[EULA](https://github.com/microsoft/powerbi-modeling-mcp/blob/main/EULA.txt) is accepted. Read it,
then choose one of these:

- **Interactively:** let the agent call `accept_eula` once, after you authorize it. The acceptance is
  saved locally.
- **Unattended:** add `--accepteula` to the args, or set `PBI_MODELING_MCP_ACCEPT_EULA=true`.

The commands below leave it out on purpose. Accepting is your decision, not a default.

## Register

`--readonly` is added deliberately. The server's default is `--readwrite`, which asks for
confirmation once per database and then applies edits. Drop `--readonly` only for a session where
changing the model is the point, and back the model up first.

**Claude Code:**

```sh
claude mcp add -s user powerbi-modeling-mcp -- npx -y @microsoft/powerbi-modeling-mcp@latest --start --readonly
```

**Copilot CLI:**

```sh
copilot mcp add powerbi-modeling-mcp -- npx -y @microsoft/powerbi-modeling-mcp@latest --start --readonly
```

Claude's `-s user` writes `~/.claude.json`, and Copilot's `add` writes `~/.copilot/mcp-config.json`.
Both are outside this repo, so these commands are the only record. `@latest` resolves on every
launch. Pin `@<version>` if a behaviour change bites.

Authentication is interactive Entra sign-in by default (`--authmode=interactive`). Service-principal
mode reads `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` and a secret or certificate from the environment.
Never put a secret in the registration command.

## Confirm

| Step | Expect |
| --- | --- |
| `claude mcp list` / `copilot mcp list` | `powerbi-modeling-mcp` connected |
| First tool call | Blocked, asking for EULA acceptance — this is correct, not a failure |
| After acceptance: *Open semantic model from PBIP folder `<path>`*, or *Connect to `<file>` in Power BI Desktop* | `connection_operations` succeeds and a read such as listing tables returns |

## Traps

- **It edits the model you point it at.** Microsoft's own warning: back up before any operation, and
  treat LLM output as possibly wrong. `--readonly` is the only hard stop.
- **Write permission on the semantic model is required**, even to connect to a model in the service.
- **Power BI Desktop connections need Desktop running on this machine**, which means Windows. PBIP
  files and Fabric workspaces work from any supported platform.
- **Non-Power BI XMLA hosts** (Azure Analysis Services, SSAS) are refused until they are listed in
  `PBI_MODELING_MCP_ALLOWED_CONNECTION_HOSTS`. Access tokens go to every listed host, so list only
  hosts your organization operates.
- **No tenant switch blocks it.** It connects through the XMLA endpoint, so only disabling XMLA stops
  it. That is an admin's concern, but it explains why a locked-down tenant may still allow it.
- **Chat logs can leak model data and metadata.** Take care sharing sessions.
