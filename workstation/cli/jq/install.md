---
tool: jq
command: jq
product: jq
verified: 2026-09-28
---

# jq — install

Binary: `jq`. Product: jq, the jqlang command-line JSON processor.

| Platform | Command |
|---|---|
| macOS | `brew install jq` |
| Windows | `scoop install jq` |

Verify with `jq --version`; it prints `jq-<version>`.

The official download page also supplies standalone macOS and Windows binaries, but this workbench
uses the platform package manager so `jq` stays on `PATH` and receives the platform's normal updates.

## Traps

- **`jq` is a JSON processor, not JavaScript.** Its filter is a separate expression language; shell
  quoting belongs to the calling shell, not to jq.
- **Do not print access tokens.** The Databricks MCP registration route uses jq only to construct an
  `Authorization` header from a CLI response. Let `databricks_mcp.py` generate that command rather
  than inspecting `.access_token` interactively.

Docs: [Download jq](https://jqlang.org/download/) · full page ingest: [reference.md](reference.md)
