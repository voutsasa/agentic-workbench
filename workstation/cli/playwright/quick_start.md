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
from playwright.sync_api import TimeoutError, sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()  # headless by default
    page = browser.new_page()
    try:
        page.goto(url, wait_until="networkidle")
    except TimeoutError:  # a site holding a connection open never goes idle
        page.goto(url, wait_until="load")
        page.wait_for_timeout(3000)
    # defuddle reads this from stdin and never sees the URL: make links absolute here
    page.eval_on_selector_all("a[href]", "els => els.forEach(e => e.setAttribute('href', e.href))")
    page.eval_on_selector_all("img[src]", "els => els.forEach(e => e.setAttribute('src', e.src))")
    html = page.content()
    browser.close()
```

Try `networkidle` first — `load` alone can fire before hydration and give you the same empty shell
`WebFetch` got. On agentskills.io (2026-09-18) `networkidle` timed out after 30 s instead, and `load`
plus a 3 s wait rendered the page; hence the fallback.

**It runs under the pipx venv's interpreter**, which is where `playwright` is importable:
`"$(pipx environment --value PIPX_LOCAL_VENVS)/playwright/bin/python" render.py` (`Scripts\python.exe` on Windows). The project `.venv` does not have it
unless the project adds it.

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
