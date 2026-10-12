---
tool: playwright
command: playwright
product: Playwright
used_by: fetch-to-markdown
verified: 2026-09-27
author: Achilleas Voutsas
version: 0.3.0
---

# playwright — install

Binary: `playwright`. Product: Playwright. Installed via Python on **both** platforms — neither brew nor scoop packages it.

| Platform | Command |
|---|---|
| macOS | `uv tool install --python 3.12 playwright` then `playwright install chromium` |
| Windows | `uv tool install --python 3.12 playwright` then `playwright install chromium` |

**`uv tool` with Python 3.12, and the user runs it.** A global Python CLI install is the one exception to
the uv-and-venv rule in [`AGENT-INSTRUCTIONS.md`](../../agent/AGENT-INSTRUCTIONS.md), where the order is
Homebrew or Scoop, then `uv tool`, then pipx. Neither brew nor scoop packages it, and on macOS `uv tool` 1.63.0 rendered a page through `render_page.py` (2026-09-27). `--python 3.12` is pinned because uv otherwise picks
whatever interpreter it finds first: 3.11.15 on macOS, 2026-09-27. An agent hands over this command and
never runs it. Upgrade with `uv tool upgrade playwright`.

**Moving from a pipx install:** run `pipx uninstall playwright` first, because both write `~/.local/bin/playwright`.
A new Playwright version needs its own browser build, so run `playwright install chromium` again after
any install or upgrade.

Verify with `playwright --version`; it prints a `1.x.y` version string.

## Workstation configuration

**Chromium only — chosen.** `playwright install chromium` fetches `chromium`, its headless shell, and `ffmpeg`. Firefox and WebKit were deliberately not taken: the ingestion route renders documentation sites and needs one engine, so the other two are download and disk for no benefit.

`p.firefox` and `p.webkit` will fail until you run:

```
playwright install firefox webkit
```

**Its Chromium is shared.** `mermaid-cli` on macOS has no browser of its own and is pointed at this one through `PUPPETEER_EXECUTABLE_PATH` — see [mermaid-cli/install.md](../mermaid-cli/install.md). Clearing `~/Library/Caches/ms-playwright` therefore breaks Mermaid rendering as well; re-run `playwright install chromium` to restore both.

## Traps

- **`playwright uninstall` removes the *current* install's browsers, not stale ones.** On 2026-09-27
  it deleted the build that the uv tool install had just fetched (1243), and kept 1234 because
  another project's `.venv` still linked to it. `~/Library/Caches/ms-playwright/.links/` records which
  installs use which builds, and other projects' venvs share this cache. To reclaim space, read those
  links first, never `--all`. Then run `playwright install chromium` again for this install.
- **`playwright install` is not optional.** The pip package ships no browsers. Skip that second step and every run fails at launch. It is a separate download of several hundred MB.
- **`uv tool` gives you the CLI, not an importable module.** To `import playwright` inside a project, add it there instead — `uv add playwright`. The two are independent installs.
- **Take the Python channel, not npm.** Playwright is published to both, and npm has generally been a minor version ahead. This workbench scripts it from Python, so the binding you write against matters more than the newer version number; a minor lag is an accepted cost, whatever the two channels read today.

Docs: [Python installation](https://playwright.dev/python/docs/intro) · full page ingest: [reference.md](reference.md)
