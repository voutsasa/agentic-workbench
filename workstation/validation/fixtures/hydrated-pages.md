# Hydrated pages

Pages whose article text is **not** in their raw HTML, so `curl` alone returns a shell and the
Playwright route is required. Section D of the validation steps converts one.

| Page | Raw | Rendered | Measured |
|---|---|---|---|
| [retire.js](https://retirejs.github.io/retire.js/) — a registered source; its vulnerability list is built client-side | 206 | 15,121 | 2026-09-20 |

Words are `defuddle parse` output: raw is the page as `curl` saves it, rendered is after
`render_page.py`. **Re-measure before trusting a row** — a site that server-renders tomorrow makes its
row useless, which is what happened to agentskills.io between 2026-09-04 and 2026-09-18.

```sh
U=<url>
curl -sL -A "Mozilla/5.0" "$U" -o /tmp/raw.html
defuddle parse /tmp/raw.html --md | wc -w
"$(pipx environment --value PIPX_LOCAL_VENVS)/playwright/bin/python" \
  ../../agent/skills/fetch-to-markdown/scripts/render_page.py "$U" /tmp/r.html
defuddle parse - --md < /tmp/r.html | wc -w
```

A ratio near 1 means the page server-renders and belongs in no row here.

## Checked and server-rendered

Kept so nobody re-tests them: every other non-GitHub, non-PDF URL in `SOURCES.md` (60 of them,
2026-09-20), and docs.cursor.com, mintlify.com/docs, docs.windsurf.com, rspress.rs, linear.app/docs,
figma.com/resource-library, notion.com/help, docs.railway.com.

App shells — excalidraw.com, mermaid.live, tldraw.com, app.gitbook.com — return nothing in raw HTML
but carry no article, so they cannot serve as a conversion fixture.

**A 404 inside a JS app looks identical to a hydrated page** in the raw-HTML test. Check the rendered
`<title>`: two candidates tried on 2026-09-20 turned out to be *"Page Not Found"*.
