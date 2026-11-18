# Evidence for the fetch-to-markdown rules

Dated measurements and per-site evidence. `SKILL.md` keeps each rule and links here.

## The JS-hydrated route

Most doc sites server-render, and agentskills.io, once the example here, now does too (2026-09-18). The register's
one hydrated page is `retirejs.github.io/retire.js/`: 206 words in the raw HTML, **15,121 rendered**,
because its vulnerability list is built client-side.

## A raw `<table>` in defuddle's output

On retire.js (`section#main_content`, 2026-09-20) defuddle alone
gave 15,137 words with one raw `<table>`; the extractor plus pandoc gave 37,297 words, markup 0,
every advisory link intact.

## A 404 in a JS app

*"Page Not Found"*
is what two candidate URLs turned out to be on 2026-09-20.

## The publisher-markdown route

Microsoft Learn's `<url>.md` is a 404, and its
HTML wraps the article in sign-in notices, "Ask Learn" and "Add to Plans" chrome that no single
selector excludes (measured on `learn.microsoft.com/en-us/fabric/iq/connectors/fabric-iq-mcp`,
2026-10-06).

What the cleaner removes — measured on `code.claude.com` and `docs.github.com`, 2026-09-26:
Mintlify's component tags (`<Note>`, `<Tabs>`, `<Tab title="…">`, `<Steps>`, `<Frame>`), GitHub Docs'
per-IDE `<div class="ghd-tool …">` wrappers, anchor-only `<a id="…" />`, raw `<ul><li>` inside table
cells, and site-relative link targets. **Fenced code blocks pass through untouched** — a `<Note>` in
an example is that example's content.

## The server-rendered route

Two more passes, both measured on docs.databricks.com (2026-09-27):

- **It writes back end tags the source left out.** Minified pages omit the optional `</td>`, `</tr>`,
  `</li>` and `</p>`. That is valid HTML5, but pandoc's HTML reader then flattens every table cell into
  its own paragraph, and no markup check can see it. The extractor closes each element where HTML5
  implies it, so the curl route keeps the table without a Playwright render.
- **It keeps only `href` and `title` on a link.** pandoc's gfm writer emits a link carrying `target`,
  `rel` or `id` as raw `<a …>` (23 on the Databricks CLI page).

### Finding the selector

A generator's own class name is a shortcut when the page has one — Docusaurus puts
`theme-doc-markdown` and `docMainContainer_` in the raw HTML (playwright.dev, dbml.dbdiagram.io,
d2lang.com, drawio.com). Where it does not, the grep above is the answer: plantuml.com's article sits
in `<main id="D7">` → `main#D7`; rdi.berkeley.edu's Jekyll syllabus in `<section class="main-content">`
→ `section.main-content`.

When no node excludes the chrome: anthropic.com/research pages put a hidden "Related articles"
block, `<div class="aside" style="visibility:hidden">`, inside `main#main-content`, which is the only
node that holds the whole article. The extractor with that selector gave markup 1. `defuddle parse
<url> --md --frontmatter` (defuddle 0.19.6) gave markup 0, no relative links, every `h3` section
heading, and a `source:` line. Measured on `components-of-agent-memory`, 2026-11-17.

## Do not use WebFetch

Verified 2026-09-04: WebFetch paraphrases the source through its own small model **even under an
explicit "verbatim, do not summarize" instruction** — the real text *"is an end-to-end test
framework"* came back as *"serves as an end-to-end testing framework"*. That fails §2 outright, and
its own description says it processes content through "a small, fast model", so this is a property of
the tool and not of any one site.

## PDF-to-text spacing

Runs of tabs and spaces between words, and a table of contents rendered as a dot-leader table, are **accepted** (2026-09-18, DDD Reference): they come from the PDF's own text layer, change no meaning, and are not normalised.

## The `.docx` figure rule

**Measured on docling 2.131.0 on Windows, 2026-10-06.** Both fixture
documents below were converted with `soffice` on `PATH` and without it. **Only a
shape needs LibreOffice**: pictures and charts came out byte-identical both ways, and a shape's text
survives either way, but the shape itself becomes an image only when `soffice` resolves. Without it,
docling prints one `WARNING … Found DrawingML elements in document, but no DOCX to PDF converters` and
exits 0. On macOS (docling 2.134.0, 2026-10-06) both ways gave byte-identical output, the shape image
included, and no `WARNING`: docling falls back to a hard-coded
`/Applications/LibreOffice.app/Contents/MacOS/soffice` when `PATH` has none
(`get_libreoffice_cmd` in `docling/backend/docx/drawingml/utils.py`), so removing `soffice` from
`PATH` there changes nothing.

Evidence: `chartex.docx` (Apache POI test data,
8 drawings = 6 charts + 2 pictures) gave 2 images, 4 placeholders and the chart data as tables;
`shapes-with-text.docx` (11 shapes, no pictures) gave every shape's text, plus 1 image only with
`soffice` on `PATH`. The first of three runs with it gave a placeholder comment instead; the next two
gave the image. A two-picture document gave 2 of 2.

## Raw `<table>` remedy

Measured on rdi.berkeley.edu/llm-agents/f24, a Jekyll syllabus: `-t gfm` gave 377 lines with one raw
`<table>` block; `-t markdown` gave 221 lines, `<table` count 0, all 21 arxiv links and all 13 lecture
rows intact.
