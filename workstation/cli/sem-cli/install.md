---
tool: sem-cli
command: sem
product: Sem (Ataraxy Labs)
verified: 2026-08-24
author: Achilleas Voutsas
version: 0.4.1
---

# sem-cli — install

Binary: `sem`. Product: Sem (Ataraxy Labs).

| Platform | Command |
|---|---|
| macOS | `brew install sem-cli` |
| Windows | `scoop install main/sem` |

Verify with `sem --version`; it prints `sem 0.x.y`.

**A machine may have it from winget rather than scoop**, in which case the binary resolves to
`…\WinGet\Packages\AtaraxyLabs.sem_…\sem.exe` and the route in force is the alternative noted below;
`winget upgrade AtaraxyLabs.sem` is then the upgrade command. Which route a given machine actually
used, and whether it is behind, is install status — it belongs in that machine's file under
[`../../machines/`](../../machines/), and acting on it is the user's call per
[`../README.md`](../README.md#version-currency--raise-it-dont-fix-it).

## Traps

- **The macOS formula is `sem-cli`, not `sem`.** `brew install sem` installs `schema-evolution-manager`, an unrelated Postgres migration tool. This is the single most likely way to end up with the wrong binary.
- **Scoop's `main/sem` *is* correct** — its manifest points at `ataraxy-labs.github.io/sem`, matching brew's `sem-cli` at the same version. The name collision is macOS-only.
- `winget install AtaraxyLabs.sem` is the vendor-documented Windows alternative if you would rather not add scoop.
- **Do not trust a version number written on this page.** A fresh install can land ahead of anything recorded here, and a recorded gap becomes misinformation the moment the channel catches up. Run `sem --version` and read the answer.

Confirm you got the right tool: `sem --help` should describe *semantic version control*, not schema migration.

Docs: [Documentation](https://ataraxy-labs.github.io/sem/) · full page ingest: [reference.md](reference.md)
