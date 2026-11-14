---
tool: scoop
command: scoop
product: Scoop
verified: 2026-10-09
author: Achilleas Voutsas
version: 0.4.2
---

# scoop — install

Binary: `scoop`. Product: Scoop, the Windows command-line installer.

| Platform | Command |
|---|---|
| macOS | N/A — Scoop is Windows-only |
| Windows | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` then `Invoke-RestMethod -Uri https://get.scoop.sh \| Invoke-Expression` |

Verify with `scoop --version`; it prints `Current Scoop version:` followed by `v0.x.x - Released at
<date>` and then each installed bucket's latest commit.

## Why it is here

Scoop is this workbench's preferred package manager on Windows, the counterpart to `brew` on macOS —
see [`../README.md`](../README.md) § *Resolving the two commands* in
[`skills/ingest-source/references/workstation-tooling.md`](../../../skills/ingest-source/references/workstation-tooling.md).
Most other `install.md` Windows rows are a `scoop install <pkg>` command; this folder documents Scoop
itself, not a package of it.

## Traps

- **A package can live in a bucket that isn't added yet.** `main` and `extras` ship with Scoop, but a
  tool in `versions`, `nerd-fonts` or a third-party bucket 404s until `scoop bucket add <name>` runs
  first. `scoop search <pkg>` across added buckets only — it does not search unregistered ones.
- **The execution-policy step is per-user, not a Scoop setting.** Skipping it is the usual cause of
  `cannot be loaded because running scripts is disabled on this system` on a fresh machine.

Docs: [scoop.sh](https://scoop.sh/) · full page ingest: [reference.md](reference.md)
