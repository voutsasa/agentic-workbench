---
tool: databricks-cli
command: databricks
product: Databricks CLI
verified: 2026-09-27
author: Achilleas Voutsas
version: 0.4.2
---

# databricks-cli — install

Binary: `databricks`. Product: Databricks CLI, the Go binary from `databricks/cli`. It holds
the OAuth login that the [Databricks MCP servers](../../mcp/databricks-mcp/setup.md)
and [`ug`](../unity-gateway/install.md) use to authenticate.

| Platform | Command |
|---|---|
| macOS | `brew tap databricks/tap && brew trust databricks/tap && brew install databricks` |
| Windows | `winget install Databricks.DatabricksCLI` |

**The user runs it, never the agent.** Both routes come from the
[Databricks install page](https://docs.databricks.com/aws/en/dev-tools/cli/install). Which route a
given machine actually used, and which Homebrew or winget version fetched it, is install status —
recorded in that machine's file under [`../../machines/`](../../machines/), not here.

Verify with `databricks --version`. It prints `Databricks CLI v<x.y.z>`, and Databricks requires
**0.205.0 or later**.

## After installing: log in once

```sh
databricks auth login --host https://<workspace-host>
databricks auth profiles        # expect your profile with Valid YES
```

This opens a browser for OAuth (user to machine) and saves the profile in `~/.databrickscfg`. No
password or token goes in that file. How to use the login is in
[`quick_start.md`](quick_start.md).

## Traps

- **Homebrew 6.0.0 and later refuse to load third-party taps until they are trusted.** Without
  `brew trust databricks/tap`, the install fails even though the tap was added.
- **PyPI `databricks-cli` is the legacy Python CLI and not this tool.** It stopped at 0.18.x and
  also installs a `databricks` command. If it is on `PATH` ahead of the Go binary,
  the version check shows a 0.x version below 0.205, and don't expect the `auth` commands
  documented here to work. Remove it (`pipx uninstall databricks-cli` or
  `pip uninstall databricks-cli`) instead of fighting the `PATH` order. See
  [*Do not cross ecosystems by name*](../README.md#do-not-cross-ecosystems-by-name).
- **`databricks aitools install` is optional.** The CLI suggests it on some commands ("Databricks
  skills are not installed"). It installs Databricks' agent skills and is not needed for the MCP
  server or for `ug`.

Docs: [Install or update the Databricks CLI](https://docs.databricks.com/aws/en/dev-tools/cli/install) ·
full page ingest: [reference.md](reference.md)
