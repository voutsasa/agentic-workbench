---
tool: dbml-cli
command: dbml2sql, sql2dbml, db2dbml
product: DBML CLI
verified: 2026-08-20
author: Achilleas Voutsas
version: 0.3.0
---

# dbml-cli — install

Binaries: `dbml2sql`, `sql2dbml`, `db2dbml` — **one package, three commands, none of them called `dbml`**. Product: DBML CLI.

| Platform | Command |
|---|---|
| macOS | `brew install dbml-cli` |
| Windows | `npm install -g @dbml/cli` |

Verify with `dbml2sql --version`; it prints a bare version number. Check all three commands — the package can install with one of them missing from `PATH`.

## The major-version boundary matters here

Behaviour across the 8 → 9 and 9 → 10 major boundaries **has not been diffed.** If a DBML round-trip
that used to work starts failing, that boundary is the first place to look.

This is the one tool in the toolchain where the two platforms have been observed on **different major
versions at the same time**, because brew and npm move independently. A round-trip that works on one
machine can therefore fail on the other for no reason other than the version gap. Compare the two
`machines/` inventories before concluding a `.dbml` file is at fault.

## Traps

- **PyPI `dbml` is not this tool.** It is a SQLAlchemy converter by a different author. DBML CLI is a Node package; there is no Python channel.
- **No scoop package.** npm is the Windows route.

Docs: [CLI docs](https://dbml.dbdiagram.io/cli/) · full page ingest: [reference.md](reference.md)
