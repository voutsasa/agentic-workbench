---
tool: playwright
command: playwright
updated: 2026-08-01
author: Achilleas Voutsas
version: 0.1.0
---

# playwright — quick start

Drives a real browser. In this workbench its job is one thing: rendering JS-hydrated doc sites that `WebFetch` returns as raw component source, so `defuddle` has real HTML to extract from.

## The ingestion route

Render the page with the skill's tested script, then hand it to defuddle — see
[`fetch-to-markdown`](../../agent/skills/fetch-to-markdown/SKILL.md) §1 for the full route:

```sh
"$(uv tool dir)/playwright/bin/python" \
  workstation/agent/skills/fetch-to-markdown/scripts/render_page.py <url> rendered.html
```

**It runs under the uv tool venv's interpreter** (`Scripts\python.exe` in place of `bin/python` on
Windows), which is where `playwright` is importable; the project `.venv` does not have it unless the
project adds it. The script waits for `networkidle` — `load` alone can fire before hydration and give
the same empty shell `WebFetch` got — and falls back to `load` plus a settle wait when a site never
goes idle, as agentskills.io did on 2026-09-18. It also makes every link absolute, because defuddle
reading stdin cannot.

## CLI subcommands

| Command | Use |
|---|---|
| `playwright screenshot <url> <file>` | one-off page capture |
| `playwright pdf <url> <file>` | page to PDF |
| `playwright open <url>` | open in a managed browser; `cr`/`ff`/`wk` pick the engine |
| `playwright codegen <url>` | record interactions and emit script code |
| `playwright install` | download browser binaries |
| `playwright show-trace` | open the trace viewer |

## Traps

- **The pip package is not the browser.** `import playwright` succeeding proves nothing: `BrowserType.launch` fails with a missing `chrome-headless-shell` until `playwright install chromium` has fetched the binaries into `ms-playwright/`. That is not optional and it is not implied by installing the tool. The command is the user's to run, in [install.md](install.md); whether a given machine has hit this is recorded in that machine's file under [`../../machines/`](../../machines/).
- **Only the engines you fetch are installed.** `p.firefox` and `p.webkit` fail until each is fetched with `playwright install <engine>`; which engines a given machine has is install status, recorded there too, not here.
- **Headless is the default and is what you want here.** No browser extension is involved in this route, despite defuddle also shipping as one.

Docs: [Library mode](https://playwright.dev/python/docs/library) — driving a browser directly, without pytest · full page ingest: [reference.md](reference.md)
