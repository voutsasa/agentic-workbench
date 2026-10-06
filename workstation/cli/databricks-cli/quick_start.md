---
tool: databricks-cli
updated: 2026-10-06
author: Achilleas Voutsas
version: 0.1.0
---

# databricks-cli — quick start

In this workbench, the Databricks CLI is used for one thing: **holding an OAuth login and handing
out short-lived tokens** to the tools that call Databricks for you, which are the
[Databricks MCP servers](../../mcp/databricks-mcp/setup.md) and
[`ug`](../unity-gateway/quick_start.md).

## Log in, and check the login

```sh
databricks auth login --host https://<workspace-host>     # first time: browser OAuth; saves a profile
databricks auth login -p <workspace name>                  # every time after: re-login to that profile
databricks auth profiles                                   # Name | Host | Valid
databricks auth describe -p <profile>                      # host, workspace_id, auth_type
```

`<workspace name>` is the profile's name in the `Name` column of `databricks auth profiles` — the first
login names it after the workspace host, e.g. `dbc-5223e681-f77d` for
`https://dbc-5223e681-f77d.cloud.databricks.com`. **Re-login whenever that column says `Valid NO`**,
then reconnect the MCP servers (`/mcp` in a running Claude Code session) and confirm with
`claude mcp list`.

`auth describe` is where the Databricks MCP setup, and `workstation/scripts/databricks_mcp.py`, get
`DBX_HOST` and `DBX_WORKSPACE_ID`. To get them as plain values:

```sh
databricks auth describe -p <profile> -o json \
  | jq '.details | {host, workspace_id: .configuration.workspace_id.value}'
```

## Get a token

```sh
databricks auth token -p <profile>
```

This prints JSON with `access_token`, `token_type` (`Bearer`), `expires_in` and `expiry`. It
returns the cached token if that is still valid and refreshes it otherwise, so a caller can run it
every time it needs a token. Claude Code's MCP `headersHelper` does exactly that, and so does
`ug mcp-proxy` for Copilot. `--force-refresh` skips the cache.

## Flags worth knowing

| Flag | Effect |
|---|---|
| `-p, --profile <name>` | Which `~/.databrickscfg` profile to use. Pass it every time. |
| `--host <url>` | Workspace URL; for `auth login`, the workspace to log in to |
| `--scopes <list>` | `auth login` only: OAuth scopes to request. The default is `all-apis`. |
| `-o json` | JSON output for `describe`, `profiles` and most other commands |
| `--debug` | Logs the requests the CLI makes, for when auth fails for no visible reason |

## Traps

- **Always pass `-p`.** Without it, the CLI uses the `DEFAULT` profile, or a `DATABRICKS_HOST` /
  `DATABRICKS_TOKEN` in the environment. That can be a different workspace from the one you mean,
  and the only sign is a `401` from the workspace you meant.
- **`Valid NO` in `auth profiles` means the refresh token has expired.** Run
  `databricks auth login -p <profile>` again. Everything that depends on the login fails until you
  do, including the MCP server.
- **Don't print tokens into a shared log or transcript.** When you only need to check that a token
  is there, pipe it through `jq '.access_token | length'`.
