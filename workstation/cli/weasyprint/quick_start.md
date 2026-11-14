---
tool: weasyprint
updated: 2026-08-01
author: Achilleas Voutsas
version: 0.4.0
---

# weasyprint — quick start

HTML and CSS rendered to PDF, with real print-CSS support — page sizes, margins, running headers, page numbers. The route to take when a deliverable needs controlled layout; it is not a headless browser and does not run JavaScript.

## Render

```
weasyprint input.html output.pdf
weasyprint -s print.css input.html output.pdf
weasyprint https://example.com output.pdf
```

Input is a URL, a filename, or `-` for stdin; output is a filename or `-` for stdout.

## Options

| Option | Effect |
|---|---|
| `-s STYLESHEET` | additional stylesheet, repeatable — the main layout control |
| `-u BASE_URL` | resolve relative asset paths, needed when reading from stdin |
| `-m MEDIA_TYPE` | media type to honour; defaults to `print` |
| `-D DPI` / `--optimize-images` / `-j QUALITY` | raster image resolution and compression |
| `--pdf-variant` | PDF/A and PDF/UA profiles — `pdf/a-3b`, `pdf/ua-1`, and others |
| `--pdf-forms` / `--pdf-tags` | interactive form fields; tagged PDF for accessibility |
| `-a FILE` | attach a file to the PDF |
| `-t TIMEOUT`, `--fail-on-http-errors` | network behaviour when fetching remote assets |

## Traps

- **No JavaScript.** WeasyPrint parses HTML and CSS only. A page that builds its content client-side renders empty — render it with Playwright first and pass the resulting HTML.
- **Not all CSS is supported.** It rejects some properties outright, warning on stderr — `text-rendering: optimizeLegibility` and `@media (max-width: …)` queries are both ignored. Warnings are not fatal, but silently dropped rules explain most layout surprises.
- **Do not drive it through pandoc.** `pandoc --pdf-engine=weasyprint` fails on pandoc's default HTML template for exactly the reason above. For plain markdown to PDF use [`pandoc --pdf-engine=typst`](../pandoc/quick_start.md); **WeasyPrint driven directly is the adopted route whenever the deliverable has a required page format**, because that is the case pandoc's template serves worst.
- **`--pdf-variant` matters for regulatory output.** PDF/A profiles are the archival formats submissions usually require.

Docs: [First steps](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) · full page ingest: [reference.md](reference.md)
