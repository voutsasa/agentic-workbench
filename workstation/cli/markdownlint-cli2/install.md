---
tool: markdownlint-cli2
command: markdownlint-cli2
product: markdownlint-cli2
verified: 2026-11-14
author: Achilleas Voutsas
version: 0.3.0
---

# markdownlint-cli2 — install

Binary: `markdownlint-cli2`. Product: markdownlint-cli2 (David Anson), a CLI for the `markdownlint` library.

| Platform | Command |
|---|---|
| macOS | `brew install markdownlint-cli2` |
| Windows | `npm install -g markdownlint-cli2` |

Verify with `markdownlint-cli2 --help`; its first line is `markdownlint-cli2 v0.x.y (markdownlint v0.x.y)`. There is no `--version` flag: it is taken as a glob, prints the same banner plus `Linting: 0 files`, and exits 0.

Runtime: Node.js ≥ 22 (`engines.node` in the npm package). The brew formula pulls in `node`; on Windows the npm route needs Node already present (`scoop install nodejs-lts`).

## Traps

- **`markdownlint-cli` is a different tool.** Same library, older CLI (`markdownlint` binary, `.markdownlintrc`, `.markdownlintignore`). markdownlint-cli2 reads neither of those two files — use `.markdownlint-cli2.jsonc` or `.markdownlint.{jsonc,yaml}`.
- **Ruby `mdl` (`markdownlint` gem) is unrelated.** Different rule set and rule IDs.
- **No scoop package** in Main or Extras. npm is the Windows route.
- **Never install through both brew and npm** — both link the same binary name; the last writer wins (see `mermaid-cli/install.md` for the observed case). Check with `ls -l "$(which markdownlint-cli2)"`.

Docs: [README](https://github.com/DavidAnson/markdownlint-cli2) · full page ingest: [reference.md](reference.md)
