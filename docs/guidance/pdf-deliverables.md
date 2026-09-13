# PDF Deliverables — Agent Guidance

**Provenance: workstation-verified** — every route and failure below was run on this machine on 1 August 2026. Re-check before trusting it after a toolchain upgrade. See [`README.md`](README.md).

How to produce a PDF on this workstation. There is **no LaTeX toolchain here and that is deliberate**, so pandoc's default PDF route fails outright — see [`workstation/cli/pandoc/install.md`](../../workstation/cli/pandoc/install.md). Two routes are adopted instead; the choice between them is about whether the page format is specified.

## Choosing a route

| | Route 1 — `pandoc --pdf-engine=typst` | Route 2 — WeasyPrint directly |
|---|---|---|
| **Reach for it when** | The content matters and the page does not — a working note, a review write-up, something to read once. | The deliverable has a required format: page size, margins, running headers, page numbers, an archival profile. |
| **Input** | Markdown, straight through | HTML + CSS you control |
| **Effort** | One command | A stylesheet to write and maintain |
| **Gives up** | Layout control; typst is not LaTeX, so `biblatex` styles, `header-includes` packages and float placement do not carry over. | Nothing, but you own the CSS. |

When in doubt start with route 1. Moving to route 2 later costs a stylesheet, not a rewrite — the markdown is unchanged.

## Route 1 — markdown to PDF

```
pandoc input.md --pdf-engine=typst -o output.pdf
```

`--pdf-engine` is **not optional**. Plain `pandoc input.md -o output.pdf` fails with `'pdflatex' not found`, because pandoc defaults to LaTeX and there is none installed.

## Route 2 — controlled layout

Convert to HTML, then render that with a print stylesheet.

Both assets live beside this file and the commands run as written from the repo root:

```
pandoc input.md -s --template=docs/guidance/minimal.html -o body.html
weasyprint -s docs/guidance/print.css body.html output.pdf
```

### Use a minimal template, not pandoc's default

[`minimal.html`](minimal.html) is three lines — an `article` wrapper around pandoc's `$body$` and nothing else.

This matters. Pandoc's built-in `-s` template embeds its own CSS, and WeasyPrint rejects several of its properties — `text-rendering: optimizeLegibility`, `overflow-x`, and `(max-width: …)` media queries — emitting warnings and silently dropping whole `@media` rules. With the minimal template the warnings disappear entirely, because pandoc's stylesheet is no longer in the document. It is also why `pandoc --pdf-engine=weasyprint` fails: same template, same rejected CSS.

### Starter stylesheet

[`print.css`](print.css) is a **starting point, not a house style** — copy it next to the deliverable and change the type and margins to suit. Verified to render A4 at 210 × 297 mm with the running header and page-number footer both present.

The four rules worth keeping unchanged:

| Rule | Why it is there |
|---|---|
| `string-set` + `content: string(...)` | Puts the current section title in the running header. The only way to get live text into a margin box. |
| `thead { display: table-header-group }` | Repeats the header row when a table spans pages. Without it a long table's columns become unreadable after page one. |
| `break-inside: avoid` | Stops rows, images and code blocks being split across a page boundary. |
| `break-after: avoid` on headings | Stops a heading stranded alone at the foot of a page. |

### Archival output

Regulatory submissions usually require a PDF/A profile:

```
weasyprint -s docs/guidance/print.css --pdf-variant pdf/a-3b body.html output.pdf
```

Verified: the `pdfaid` identifier appears in the output only when `--pdf-variant` is passed. WeasyPrint also offers `pdf/a-1b` through `pdf/a-4f`, `pdf/ua-1` and `pdf/ua-2` for accessibility, and the `pdf/x-*` print-production profiles. `--pdf-tags` adds the structure tagging that PDF/UA depends on.

## Traps

- **No JavaScript in route 2.** WeasyPrint parses HTML and CSS only. Content built client-side renders empty; render it with Playwright first and pass the resulting HTML.
- **Unsupported CSS is dropped with a warning, not an error.** Check stderr — silently ignored rules explain most layout surprises. That is diagnosis, not noise.
- **Do not install LaTeX to "fix" route 1.** It would re-enable pandoc's default engine and produce output that differs from what this guidance describes. If a genuine LaTeX need appears, raise it.
- **Markdown deliverables in this repo are not PDFs.** They must render in Zed's plain preview — no inline HTML, no CSS assets. This guidance is for producing an artefact *from* a document, not for how the source document is written.

## Related

- [`workstation/cli/pandoc/quick_start.md`](../../workstation/cli/pandoc/quick_start.md) — pandoc's formats and flags
- [`workstation/cli/weasyprint/quick_start.md`](../../workstation/cli/weasyprint/quick_start.md) — the full option list
- [`workstation/cli/playwright/quick_start.md`](../../workstation/cli/playwright/quick_start.md) — rendering a JS page to HTML first
