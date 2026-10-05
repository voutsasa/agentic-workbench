---
tool: unity-gateway
command: ug, ucode
product: Unity Gateway (Databricks)
verified: 2026-09-27
author: Achilleas Voutsas
version: 0.1.0
---

# unity-gateway — install

Binaries: `ug`, plus `ucode` (the old name, still supported). Product: Databricks Unity Gateway,
from `databricks/unity-gateway`. It is a Python tool, installed straight from GitHub; it is not
packaged for brew, scoop or PyPI.

| Platform | Command |
|---|---|
| macOS | `uv tool install --python 3.12 git+https://github.com/databricks/unity-gateway` |
| Windows | `uv tool install --python 3.12 git+https://github.com/databricks/unity-gateway` |

**`uv tool` with Python 3.12, and the user runs it.** This is upstream's own route, with the Python
version pinned. It is the second choice in this workbench's order for global Python CLIs (Homebrew or
Scoop, then `uv tool`, then pipx; see [`AGENT-INSTRUCTIONS.md`](../../agent/AGENT-INSTRUCTIONS.md)),
and neither brew nor scoop packages it. Whatever route a given machine used, and whether it has been
run there at all, goes in [`../../machines/`](../../machines/), not here.

**Moving from a pipx install:** run `pipx uninstall unity-gateway` first. Both routes install
`~/.local/bin/ug`, so leaving the old copy in place makes the two collide. Uninstalling leaves `ug`'s
state in `~/.ucode/` untouched (observed on 2026-09-27, moving between the two routes).

Verify with `ug --version`. It prints a bare version such as `0.2.0+29.ge43c341`, where the
`+<n>.g<sha>` suffix is the git build it was installed from.

**Requirements:** Python 3.12 or later (pinned by `--python 3.12` above), and the
[Databricks CLI](../databricks-cli/install.md), logged in. `npm` is needed only if you let `ug`
install an agent CLI for you, which is not a route this workbench uses.

## Do you need it?

**Only for GitHub Copilot CLI.** Copilot reaches the [Databricks MCP servers](../../mcp/databricks-mcp/setup.md)
through `ug mcp-proxy`, a stdio bridge that injects a fresh token into every request, because
Copilot's own config takes only static headers. Claude Code doesn't need `ug`: its
`headersHelper` needs only the Databricks CLI.

`ug` can also set coding agents up to run *through* Databricks AI Gateway. This workbench doesn't
use that. Read the traps in [`quick_start.md`](quick_start.md) before running any `ug` command
other than `mcp-proxy`.

## Traps

- **PyPI `ug` is a different project.** It is `thorwhalen/ug`, "Utils using Google API".
  **PyPI `unity-gateway` is a `0.0.0b0` placeholder** that doesn't link to `databricks/unity-gateway`.
  Install only from the GitHub URL above. See
  [*Do not cross ecosystems by name*](../README.md#do-not-cross-ecosystems-by-name).
- **`ug upgrade` changes the version in place,** and so does `uv tool upgrade unity-gateway`. Both
  are upgrades, so they are the user's call, never an agent's.
- **Migrating from `ucode`:** upstream says to run `uv tool uninstall ucode` first, then the install above.

Docs: [Unity Gateway README](https://github.com/databricks/unity-gateway) ·
[ug CLI reference](https://docs.databricks.com/aws/en/ai-gateway/coding-agent-ug-cli) ·
full page ingest: [reference.md](reference.md)
