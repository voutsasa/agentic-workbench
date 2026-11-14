---
tool: brew
updated: 2026-10-09
author: Achilleas Voutsas
version: 0.4.2
---

# brew — quick start

macOS/Linux package manager. In this workbench it is the preferred macOS route named in every other
tool's `install.md` macOS row — read it when resolving or troubleshooting one of those commands, not
usually on its own. Not independently run on this machine (Windows-only workstation); the invocations
below come from [`brew.sh`](https://brew.sh/) and `docs.brew.sh`, not a local session.

## Common invocations

```sh
brew install <formula>              # install a package (a "formula")
brew install --cask <app>           # install a GUI application (a "cask")
brew info --formula <name>          # confirm a formula is genuine before trusting a route
brew upgrade <formula>              # upgrade one package
brew update                         # refresh Homebrew's own formula index first
brew --prefix                       # where Homebrew is installed on this machine
brew --cellar                       # where a formula's files actually live
```

| Term | Meaning |
|---|---|
| Formula | A command-line package's install recipe |
| Cask | A GUI application's install recipe |
| Cellar | Where each package's own versioned files live, e.g. `$(brew --cellar)/ffmpeg` |
| Prefix | The symlink target on `PATH`, e.g. `/opt/homebrew` |

## Traps

- **Run `brew update` before `brew upgrade`.** Homebrew's local formula index can lag the project's own
  release; `brew upgrade` only sees what the index already knows.
- **A formula resolving is not proof it's the right package.** Cross-check its homepage against the
  `SOURCES.md` URL — see [`../README.md`](../README.md) § *Do not cross ecosystems by name*.

Docs: [docs.brew.sh](https://docs.brew.sh/) · full page ingest: [reference.md](reference.md)
