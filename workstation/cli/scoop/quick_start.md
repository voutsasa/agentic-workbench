---
tool: scoop
updated: 2026-10-09
author: Achilleas Voutsas
version: 0.2.0
---

# scoop — quick start

Windows package manager. In this workbench it is the preferred Windows route named in every other
tool's `install.md` Windows row — read it when resolving or troubleshooting one of those commands,
not usually on its own.

## Common invocations

```
scoop install <pkg>                 # from an already-added bucket
scoop bucket add extras             # add a non-default bucket before installing from it
scoop bucket list                   # which buckets are added on this machine
scoop search <pkg>                  # across added buckets only
scoop update <pkg>                  # upgrade one package
scoop status                        # which installed packages are outdated
```

Buckets observed on this machine, 2026-10-09: `main`, `extras`, `versions`, `java`.

| Flag / subcommand | Use |
|---|---|
| `scoop install <bucket>/<pkg>` | pin the bucket explicitly when the same name exists in more than one |
| `scoop update *` | upgrade every installed package |
| `scoop cleanup <pkg>` / `scoop cleanup *` | remove old versions after an update |
| `scoop uninstall <pkg>` | remove a package and its shim |

## Traps

- **`scoop search` only covers added buckets.** A hit nowhere does not mean the package is unpublished
  — check [`workstation/cli/README.md`](../README.md) § *Do not cross ecosystems by name* and the
  bucket-resolution check in
  [`skills/ingest-source/references/workstation-tooling.md`](../../../skills/ingest-source/references/workstation-tooling.md)
  before concluding a tool isn't on Scoop.
- **A shim does not mean the package is current.** `scoop status` is the only command that reports a
  version lag; `scoop list` just shows what's installed.

Docs: [scoop.sh](https://scoop.sh/) · full page ingest: [reference.md](reference.md)
