---
tool: playwright
command: playwright
product: Playwright
verified: 2026-08-20
---

# playwright — install

Binary: `playwright`. Product: Playwright. Installed via Python on **both** platforms — neither brew nor scoop packages it.

| Platform | Command |
|---|---|
| macOS | `pipx install playwright` then `playwright install chromium` |
| Windows | `pipx install playwright` then `playwright install chromium` |

**`pipx`, not `uv tool`, and the user runs it.** A global Python CLI install is the one exception to the
uv-and-venv rule in [`AGENT-INSTRUCTIONS.md`](../../agent/AGENT-INSTRUCTIONS.md); an agent hands over
these commands and never runs them.

Verify with `playwright --version`; it prints a `1.x.y` version string.

## Workstation configuration

**Chromium only — chosen.** `playwright install chromium` fetches `chromium`, its headless shell, and `ffmpeg`. Firefox and WebKit were deliberately not taken: the ingestion route renders documentation sites and needs one engine, so the other two are download and disk for no benefit.

`p.firefox` and `p.webkit` will fail until you run:

```
playwright install firefox webkit
```

**Its Chromium is shared.** `mermaid-cli` on macOS has no browser of its own and is pointed at this one through `PUPPETEER_EXECUTABLE_PATH` — see [mermaid-cli/install.md](../mermaid-cli/install.md). Clearing `~/Library/Caches/ms-playwright` therefore breaks Mermaid rendering as well; re-run `playwright install chromium` to restore both.

## Traps

- **`playwright install` is not optional.** The pip package ships no browsers. Skip that second step and every run fails at launch. It is a separate download of several hundred MB.
- **`pipx` gives you the CLI, not an importable module.** To `import playwright` inside a project, add it there instead — `uv add playwright`. The two are independent installs.
- **Take the Python channel, not npm.** Playwright is published to both, and npm has generally been a minor version ahead. This workbench scripts it from Python, so the binding you write against matters more than the newer version number; a minor lag is an accepted cost, whatever the two channels read today.

Docs: [Python installation](https://playwright.dev/python/docs/intro) · full page ingest: [reference.md](reference.md)
