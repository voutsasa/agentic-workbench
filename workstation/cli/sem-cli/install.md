---
tool: sem-cli
command: sem
product: Sem (Ataraxy Labs)
verified: 2026-08-24
---

# sem-cli
 — install

Binary: `sem`. Product: Sem (Ataraxy Labs).

| Platform | Command |
|---|---|
| macOS | `brew install sem-cli` |
| Windows | `scoop install main/sem` |

Verify with `sem --version`; it prints `sem 0.x.y`.

**Windows, 24 August 2026: `sem 0.13.0`, and it came from winget, not scoop.** The binary resolves to
`…\WinGet\Packages\AtaraxyLabs.sem_…\sem.exe`, so the route in force is the alternative noted below.
That install is nine minor versions behind this page's `version_observed` and ten behind brew stable —
a stale local install, clearable with `winget upgrade AtaraxyLabs.sem`. Not upgraded: per
[`../README.md`](../README.md#version-currency--raise-it-dont-fix-it) that is the user's call.

## Traps

- **The macOS formula is `sem-cli`, not `sem`.** `brew install sem` installs `schema-evolution-manager`, an unrelated Postgres migration tool. This is the single most likely way to end up with the wrong binary.
- **Scoop's `main/sem` *is* correct** — its manifest points at `ataraxy-labs.github.io/sem`, matching brew's `sem-cli` at the same version. The name collision is macOS-only.
- `winget install AtaraxyLabs.sem` is the vendor-documented Windows alternative if you would rather not add scoop.
- **The pinned version is what is installed here, not what brew ships.** `version_observed` is 0.22.1; brew's stable was 0.23.1 on 24 August 2026, so a fresh install lands ahead of this page. Re-run `sem --version` rather than trusting the number.

Confirm you got the right tool: `sem --help` should describe *semantic version control*, not schema migration.

Docs: [Documentation](https://ataraxy-labs.github.io/sem/) · full page ingest: [reference.md](reference.md)
