---
tool: typst
command: typst
product: Typst
used_by: pdf-deliverable
verified: 2026-09-18
author: Achilleas Voutsas
version: 0.4.0
---

# typst — install

Binary: `typst`. Product: Typst. Self-contained Rust binary; no runtime dependency.

| Platform | Command |
|---|---|
| macOS | `brew install typst` |
| Windows | `scoop install main/typst` |

Verify with `typst --version`; it prints `typst 0.x.y`.

## Why it is here

`pandoc` has no working PDF default on this workstation — it defaults to LaTeX, which is deliberately
not installed — so markdown to PDF runs `pandoc --pdf-engine=typst`. Without `typst` on `PATH` that
route fails. See [`../pandoc/install.md`](../pandoc/install.md).

## Traps

- **PyPI `typst` is not this tool.** It is `messense/typst-py`, a Python binding with no `typst`
  command. npm `typst` is `typst-community/typst.js`, a JavaScript wrapper. Neither puts the CLI on
  `PATH`; use the routes above. See [*Do not cross ecosystems by name*](../README.md#do-not-cross-ecosystems-by-name).

Docs: [typst/typst](https://github.com/typst/typst) · full page ingest: [reference.md](reference.md)
