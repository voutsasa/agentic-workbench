---
tool: brew
command: brew
product: Homebrew
verified: 2026-10-09
author: Achilleas Voutsas
version: 0.3.0
---

# brew — install

Binary: `brew`. Product: Homebrew, the macOS/Linux package manager.

| Platform | Command |
|---|---|
| macOS | `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"` |
| Windows | N/A — Homebrew does not run natively on Windows; only inside WSL, where it follows the macOS/Linux route |

Verify with `brew --version`; it prints `Homebrew x.y.z`. Not independently observed on this machine
(Windows-only workstation) — recorded from [`brew.sh`](https://brew.sh/) rather than a local run; see
[`../README.md`](../README.md) § *Route here, state in `machines/`*.

A macOS `.pkg` installer is also offered for interactive or unattended MDM installs, from
[Homebrew's latest GitHub release](https://github.com/Homebrew/brew/releases/latest).

## Why it is here

Homebrew is this workbench's preferred package manager on macOS, the counterpart to `scoop` on
Windows — see [`../README.md`](../README.md) § *Resolving the two commands* in
[`skills/ingest-source/references/workstation-tooling.md`](../../../skills/ingest-source/references/workstation-tooling.md).
Most other `install.md` macOS rows are a `brew install <formula>` command; this folder documents
Homebrew itself, not a formula of it.

## Traps

- **Install prefix differs by platform.** `/opt/homebrew` on Apple Silicon, `/usr/local` on Intel
  macOS, `/home/linuxbrew/.linuxbrew` on Linux/WSL — a hard-coded `/usr/local` path in a script breaks
  on Apple Silicon.
- **A formula name resolving is not evidence it is the right package** — see
  [`../README.md`](../README.md) § *Do not cross ecosystems by name* and `brew info --formula <name>`
  before trusting a route.

Docs: [brew.sh](https://brew.sh/) · full page ingest: [reference.md](reference.md)
