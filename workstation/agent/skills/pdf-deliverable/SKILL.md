---
name: pdf-deliverable
description: Produce a PDF from markdown or HTML without LaTeX — pandoc via typst for a working note, WeasyPrint with a print stylesheet when the page format is specified (page size, margins, running headers, page numbers, PDF/A/UA archival profiles). Use when asked to make, export, render or hand over a PDF, when `pandoc -o out.pdf` has failed with `'pdflatex' not found`, or when a deliverable has to meet a submission format. Not for how a markdown source document is written.
author: Achilleas Voutsas
version: 0.3.0
---

# PDF deliverables

**`pandoc input.md -o output.pdf` fails on a machine with no LaTeX** — pandoc defaults to `pdflatex`
and reports `'pdflatex' not found. Please select a different --pdf-engine or install 'pdflatex'`. Two
routes replace it. The choice between them is one question: **is the page format specified?**

## Choosing a route

| | Route 1 — `pandoc --pdf-engine=typst` | Route 2 — WeasyPrint directly |
|---|---|---|
| **Reach for it when** | The content matters and the page does not — a working note, a review write-up, something to read once. | The deliverable has a required format: page size, margins, running headers, page numbers, an archival profile. |
| **Input** | Markdown, straight through | HTML + CSS you control |
| **Effort** | One command | A stylesheet to write and maintain |
| **Gives up** | Layout control. typst is not LaTeX, so `biblatex` styles, `header-includes` packages and float placement do not carry over. | Nothing, but you own the CSS. |

**When in doubt start with route 1.** Moving to route 2 later costs a stylesheet, not a rewrite — the
markdown is unchanged.

**Do not install LaTeX to "fix" route 1.** It re-enables pandoc's default engine and produces output
that differs from what this skill describes. If a genuine LaTeX need appears, raise it with the user
rather than installing anything — installing is the user's to run, never the agent's.

## Route 1 — markdown to PDF

```sh
pandoc input.md --pdf-engine=typst -o output.pdf
```

`--pdf-engine` is **not optional**; it is the whole point of the route.

## Route 2 — controlled layout

Convert to HTML with a minimal template, then render that with a print stylesheet. Both assets ship
with this skill, so the commands run from any directory:

```sh
pandoc input.md -s --template="$HOME/.claude/skills/pdf-deliverable/assets/minimal.html" -o body.html
weasyprint -s "$HOME/.claude/skills/pdf-deliverable/assets/print.css" body.html output.pdf
```

**`$HOME` and not `~`.** A tilde is not expanded after an `=` — verified in both bash and zsh,
`--template=~/x` reaches pandoc as the literal four characters `~/x`. Separate-argument forms like
WeasyPrint's `-s ~/x` do expand, so the two commands above would behave differently for the same
reason one is written with `=` and the other is not. `$HOME` expands in both positions, so use it in
both.

### Use the minimal template, not pandoc's default

[`assets/minimal.html`](assets/minimal.html) is three lines — an `article` wrapper around pandoc's
`$body$` and nothing else.

This matters. **Pandoc's built-in `-s` template embeds its own CSS, and WeasyPrint rejects several of
its properties** — `text-rendering: optimizeLegibility`, `overflow-x`, and `(max-width: …)` media
queries — emitting warnings and silently dropping whole `@media` rules. With the minimal template the
warnings disappear entirely, because pandoc's stylesheet is no longer in the document.

It is also why `pandoc --pdf-engine=weasyprint` fails: same template, same rejected CSS.

### Starter stylesheet

[`assets/print.css`](assets/print.css) is a **starting point, not a house style** — copy it next to the
deliverable and change the type and margins to suit. It renders A4 at 210 × 297 mm with the running
header and page-number footer both present.

Four rules are worth keeping unchanged:

| Rule | Why it is there |
|---|---|
| `string-set` + `content: string(...)` | Puts the current section title in the running header. The only way to get live text into a margin box. |
| `thead { display: table-header-group }` | Repeats the header row when a table spans pages. Without it a long table's columns are unreadable after page one. |
| `break-inside: avoid` | Stops rows, images and code blocks being split across a page boundary. |
| `break-after: avoid` on headings | Stops a heading stranded alone at the foot of a page. |

### Archival output

Regulatory submissions usually require a PDF/A profile:

```sh
weasyprint -s "$HOME/.claude/skills/pdf-deliverable/assets/print.css" \
  --pdf-variant pdf/a-3b body.html output.pdf
```

**The profiles are not a contiguous range.** Read the list off the installed tool —
`weasyprint --help` prints the exact set — rather than assuming `pdf/a-<n><letter>` exists. As of
WeasyPrint 70 it is `pdf/a-1b`, `a-2b`, `a-3b`, `a-2u`, `a-3u`, `a-4u`, `a-1a`, `a-2a`, `a-3a`,
`a-4e`, `a-4f`, plus `pdf/ua-1`, `pdf/ua-2` and the `pdf/x-*` print-production profiles. `--pdf-tags`
adds the structure tagging PDF/UA depends on.

**Verifying the profile landed:** the `pdfaid` identifier is written only when `--pdf-variant` is
passed — but **WeasyPrint compresses the XMP metadata by default, so grepping the PDF finds nothing
either way.** Add `--uncompressed-pdf` to check, then re-render without it:

```sh
weasyprint -s <css> --pdf-variant pdf/a-3b --uncompressed-pdf body.html check.pdf
grep -a -o 'pdfaid:part="[0-9]*" pdfaid:conformance="[A-Z]*"' check.pdf
# pdfaid:part="3" pdfaid:conformance="B"
```

A `0` from that grep on a *compressed* file is not evidence the variant was ignored.

## Traps

- **No JavaScript in route 2.** WeasyPrint parses HTML and CSS only. Content built client-side renders
  empty; render it with Playwright first and pass the resulting HTML.
- **Unsupported CSS is dropped with a warning, not an error.** Check stderr — silently ignored rules
  explain most layout surprises. That is diagnosis, not noise.
- **A PDF is an artefact made *from* a document, not a way of writing one.** If the repo's own markdown
  has to render in a plain previewer, it still gets no inline HTML and no CSS assets. This skill
  produces the export; it does not change how the source is written.

## Before trusting any of the above

Every claim here is about **tool behaviour**, so it holds only where those tools are installed. Two
things to check on an unfamiliar machine, in this order:

1. **The machine note** — `~/.agentic-workbench/machine.md`, where one exists, records which of the
   CLI toolchain actually runs there. A tool named here and missing there is a blocker to report, not to route around.
2. **`typst` is not part of pandoc.** It is a separate binary that pandoc shells out to, and it is not
   probed by the standard inventory. `command -v typst` settles it. Route 1 fails without it exactly
   the way the LaTeX default does.

Where this repo's per-tool guidance is available, it carries the full flag lists:
`workstation/cli/pandoc/quick_start.md`, `workstation/cli/weasyprint/quick_start.md`, and
`workstation/cli/playwright/quick_start.md` for rendering a JS page to HTML first.
