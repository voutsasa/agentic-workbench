---
tool: jq
updated: 2026-09-28
author: Achilleas Voutsas
version: 0.4.0
---

# jq — quick start

`jq` selects, transforms, and validates JSON on the command line. In this workbench it supports
Claude Code's Databricks MCP `headersHelper`; the generated registration command owns that use.

## Common invocations

```sh
databricks auth profiles -o json | jq '.'             # format JSON without exposing a token
databricks auth describe -p <profile> -o json | jq '.details.host'
databricks auth describe -p <profile> -o json | jq -r '.details.configuration.workspace_id.value'
```

| Flag | Use |
|---|---|
| `-r` | Print a string without JSON quotes; use for a shell value. |
| `-c` | Emit compact JSON on one line; use for a protocol header or JSON Lines. |
| `-e` | Exit non-zero when the final result is `false` or `null`; use as a predicate in a script. |
| `--arg name value` | Pass a shell value as a JSON string without interpolation or quote hazards. |

## Traps

- **Quote filters for the calling shell.** In PowerShell, prefer single quotes: `jq '.details.host'`.
  Do not concatenate an untrusted shell value into a jq filter; pass it with `--arg`.
- **`-r` changes the output contract.** Without it, a JSON string includes quotes; with it, `null`
  becomes the literal text `null`. Use `-e` when a missing value must fail rather than flow onward.
- **A token is still sensitive after jq transforms it.** Never direct `databricks auth token` output
  or a constructed `Authorization` header into a transcript, file, or committed configuration.

Docs: [Manual](https://jqlang.org/manual/) · full page ingest: [reference.md](reference.md)
