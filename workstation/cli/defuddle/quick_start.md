---
tool: defuddle
updated: 2026-08-01
author: Achilleas Voutsas
version: 0.4.1
---

# defuddle — quick start

Strips a web page down to its article content — no nav bars, cookie banners, sidebars, or "Edit this page" links. The second half of the JS-hydrated ingestion route, after Playwright has rendered the DOM.

## The ingestion invocation

```
defuddle parse <url> --md --frontmatter -o "docs/landing-zone/<topic name>.md"
```

`--md` converts to markdown, `--frontmatter` prepends YAML with title, author, source and domain — which is what the ingested pages in this repo carry at the top.

For a page Playwright has already rendered, feed the HTML in rather than refetching:

```
defuddle parse - --md --frontmatter < rendered.html
```

## Options

| Option | Effect |
|---|---|
| `-m`, `--markdown` (`--md`) | convert extracted content to markdown |
| `-f`, `--frontmatter` | prepend YAML metadata block |
| `-j`, `--json` | emit JSON with metadata and content instead |
| `-p, --property <name>` | extract one property only, e.g. `title`, `description`, `domain` |
| `-o, --output <file>` | write to a file rather than stdout |
| `-u, --user-agent <string>` | custom UA — the fix when a site answers 403 |
| `-l, --lang <code>` | preferred language, BCP 47 |

The only subcommand is `parse`; the source argument is a file path, a URL, or `-` for stdin.

## Traps

- **A 403 is usually the User-Agent.** Set `-u` before concluding the site is unfetchable.
- **Defuddle alone cannot see hydrated content.** If the page is a JS app, `defuddle parse <url>` extracts the empty shell. Render with Playwright first — see [`fetch-to-markdown`](../../agent/skills/fetch-to-markdown/SKILL.md) §1.

Docs: [README](https://github.com/kepano/defuddle) · full page ingest: [reference.md](reference.md)
