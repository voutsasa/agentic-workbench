---
tool: playwright
command: playwright
updated: 2026-08-01
---

# playwright — quick start

Drives a real browser. In this workbench its job is one thing: rendering JS-hydrated doc sites that `WebFetch` returns as raw component source, so `defuddle` has real HTML to extract from.

## The ingestion route

Render the page, then hand it to defuddle — see [`fetch-to-markdown`](../../agent/skills/fetch-to-markdown/SKILL.md) §1.

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()          # headless by default
    page = browser.new_page()
    page.goto(url, wait_until="networkidle")
    html = page.content()
    browser.close()
```

`wait_until="networkidle"` is the part that matters — the default waits for `load`, which fires before hydration and gives you the same empty shell `WebFetch` got.

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

- **Chromium is the only engine installed here**, by choice — see [install.md](install.md). `p.firefox` and `p.webkit` fail until the others are fetched.
- **Headless is the default and is what you want here.** No browser extension is involved in this route, despite defuddle also shipping as one.

Docs: [Library mode](https://playwright.dev/python/docs/library) — driving a browser directly, without pytest · full page ingest: [reference.md](reference.md)
