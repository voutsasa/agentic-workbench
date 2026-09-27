---
name: fetch-to-markdown
description: Fetch one web page, PDF or Office document and convert it to clean local markdown — classify the source, route it to the right tool (raw README, curl, HTML node extractor plus pandoc, docling, soffice for legacy binary formats, or Playwright plus defuddle), quality-check the result against the original, and strip embedded base64 images. Use when asked to fetch, retrieve, scrape, ingest or convert a docs page, README, PDF, .docx, .doc, .pptx or .ppt into markdown at a given path. Not for general web research — this writes a file.
---

# Fetch a document to markdown

One source URL, one destination path, clean markdown at the end of it.

**The caller owns the destination.** This skill does not choose the directory, derive the filename, or
record the result anywhere — a project that wants those decisions made for it wraps this skill and
makes them itself. If the request did not name a destination path, ask for one before fetching.

`<skill>` below is this skill's own directory; `<dest>` is the destination path the caller gave.

## 1. Classify the source, then route it

| The source is | Route | Command |
|---|---|---|
| `github.com/<owner>/<repo>` | **Raw README only. Never clone.** | `curl -s https://raw.githubusercontent.com/<owner>/<repo>/<branch>/README.md` |
| **A page whose publisher serves its own markdown** — Mintlify (`code.claude.com`, `platform.claude.com`, `modelcontextprotocol.io`), GitHub Docs. **Probe for this first**, whatever else the page looks like | `curl <url>.md` → clean the publisher's components | see below |
| A direct `.pdf` | Fetch the file itself, never scrape a rendered viewer | `curl -sL -o "<dest>.pdf" <url>` |
| A local or fetched PDF / Office document | `docling` — real layout understanding, ahead of pandoc | `docling convert <input> --to md --output <dir>` |
| A legacy binary `.doc` or `.ppt` | Two-step — neither docling nor pandoc reads the old binary format | see below |
| **Any server-rendered HTML** — Docusaurus, Sphinx, ReadTheDocs, MkDocs, VitePress, mdBook, Jekyll, a classic blog, hand-rolled | curl → extract the article node → pandoc | see below |
| A JS-hydrated platform (Fern, Rspress — anything whose raw HTML holds no article text) | Playwright → defuddle | headless; see below |

**One route covers every server-rendered page**, because the extractor's selector is an argument.
Splitting it by generator only invited the question *which of these is Docusaurus* when the answer
never changed the command. Confirm the text is in the raw HTML — `curl -s <url> | grep -c "<some
sentence from the page>"` — and if it is, this route works whatever built the page.

### The JS-hydrated route

Confirm the route is needed first with the same `curl | grep -c` test as above — most doc sites
server-render, and agentskills.io, once the example here, now does too (2026-09-18). The register's
one hydrated page is `retirejs.github.io/retire.js/`: 206 words in the raw HTML, **15,121 rendered**,
because its vulnerability list is built client-side. Then:

```sh
"$(uv tool dir)/playwright/bin/python" \
  <skill>/scripts/render_page.py <url> <tmp>/rendered.html
defuddle parse - --md --frontmatter < <tmp>/rendered.html > "<dest>.md"
```

**Run `render_page.py` with the uv tool venv's interpreter** — it is the one script here that needs
`playwright`, and exits 2 naming that interpreter when run under any other. It handles the two traps
measured on agentskills.io on 2026-09-18:

- **`wait_until="networkidle"` can time out** on a site that keeps a connection open — `Page.goto:
  Timeout 30000ms exceeded`. The script falls back to `load` plus a settle wait (`--settle-ms`).
- **defuddle reading stdin cannot resolve relative links** — it never sees the page URL and has no
  option to take one, so `](/clients)` would survive and fail §2's link check. The script rewrites
  every `href` and `src` to its absolute value in the browser before capturing the HTML.

**A raw `<table>` in defuddle's output is the §2 table case**, and the remedy below applies to the
rendered HTML: feed `<tmp>/rendered.html` to `extract_article.py` with the article's selector and
convert with `pandoc -t markdown`. On retire.js (`section#main_content`, 2026-09-20) defuddle alone
gave 15,137 words with one raw `<table>`; the extractor plus pandoc gave 37,297 words, markup 0,
every advisory link intact.

**A 404 in a JS app looks exactly like a hydrated page** to the `curl | grep -c` test — both have no
text in the raw HTML. Check the rendered `<title>` before trusting the conversion: *"Page Not Found"*
is what two candidate URLs turned out to be on 2026-09-20.

### The legacy `.doc` / `.ppt` route

`soffice` converts the old binary formats to PDF; docling then reads that PDF like any other:

```sh
soffice --headless --convert-to pdf --outdir <tmp> <input>
docling convert <tmp>/<stem>.pdf --to md --output <dir>
```

A 0-byte or missing `<tmp>/<stem>.pdf` means `soffice` failed silently — common on a locked or
corrupt source file. Report it; don't retry blindly. `soffice` may need its `program` directory
prepended to `PATH` for this run — check the machine note for the exact path and whether a shim
already resolves it.

### The publisher-markdown route

**Probe every page for this before choosing any other route**, because the HTML routes also produce
a file and lose more doing it:

```sh
curl -sLI <url>.md | grep -i "^content-type: text/markdown"
```

A hit means the platform serves the page's own markdown source, which is the text itself rather than
a conversion of it — no selector to choose, no pandoc writer to lose a table to, no model anywhere.
Then:

```sh
curl -sL <url>.md -o <tmp>/served.md
python3 <skill>/scripts/clean_publisher_md.py <tmp>/served.md "<dest>.md" <url>
python3 <skill>/scripts/add_frontmatter.py "<dest>.md" <tmp>/page.html <url>
```

**Pass the page's own URL, not the site root**, as in the server-rendered route and for the same
reason: root-relative, sibling and parent link targets all resolve against it. A site root alone
leaves the sibling links `modelcontextprotocol.io` writes between its own docs pages pointing at
nothing — the script's docstring spells the three forms out. `add_frontmatter.py` still needs the
rendered HTML, so fetch that too.

**What the cleaner removes** — measured on `code.claude.com` and `docs.github.com`, 2026-09-26:
Mintlify's component tags (`<Note>`, `<Tabs>`, `<Tab title="…">`, `<Steps>`, `<Frame>`), GitHub Docs'
per-IDE `<div class="ghd-tool …">` wrappers, anchor-only `<a id="…" />`, raw `<ul><li>` inside table
cells, and site-relative link targets. **Fenced code blocks pass through untouched** — a `<Note>` in
an example is that example's content.

Two things it cannot fix, both properties of the source rather than the conversion: a code sample the
site itself stores without line breaks comes out on one line whichever route you take, and a relative
link *inside a quoted example file* is correct as it stands. Say so in the hand-back; do not hand-edit
the corpus.

### The server-rendered route

```sh
curl -sL -A "Mozilla/5.0" <url> -o <tmp>/page.html
python3 <skill>/scripts/extract_article.py <tmp>/page.html <tag|tag.class|tag#id|tag[attr=value]> <url> \
  | pandoc -f html -t gfm -o "<dest>.md"
python3 <skill>/scripts/add_frontmatter.py "<dest>.md" <tmp>/page.html <url>
```

**Always pass the page's own URL as the third argument.** It resolves relative `href`/`src` targets
against it. Skip it and a link like `./assets/<file>.pdf` converts perfectly and points at nothing —
the markdown is well-formed, so no markup check below can see it.

`extract_article.py` pulls one HTML node by `tag.class`, `tag#id` or `tag[attr=value]` and strips what
pandoc's gfm writer cannot map cleanly — `div`, `header`, `span`, `section`, inline `<svg>`, icon
`<img>`s, `<style>`, empty bookmark anchors — and the chrome that sites put *inside* the article node:
Antora's breadcrumbs and pagination, an "On this page" aside. The source's own text passes through
untouched.

`add_frontmatter.py` then prepends the corpus frontmatter block — `title`, `site`, `source`, `domain`,
`language`, `description`, `word_count` — that defuddle writes itself with `--frontmatter` on the
other routes, so provenance reads the same whichever route produced the file. It reads the page's own
`<title>`, `<html lang>` and meta tags, omits a field the page lacks, and leaves a file that already
starts with `---` untouched, so re-running it changes nothing.

#### Finding the selector

The only judgement call in this route. List the candidate containers and pick the one wrapping the
article:

```sh
grep -oE "<(main|article|div|section)[^>]{0,120}" <tmp>/page.html \
  | grep -iE "class=|id=" | sort | uniq -c | sort -rn | head -20
```

A generator's own class name is a shortcut when the page has one — Docusaurus puts
`theme-doc-markdown` and `docMainContainer_` in the raw HTML (playwright.dev, dbml.dbdiagram.io,
d2lang.com, drawio.com). Where it does not, the grep above is the answer: plantuml.com's article sits
in `<main id="D7">` → `main#D7`; rdi.berkeley.edu's Jekyll syllabus in `<section class="main-content">`
→ `section.main-content`.

**Pick the narrowest node that still holds everything you want.** Too wide drags in nav and footer,
which §2's noise check catches; too narrow silently drops content, which it does not — so confirm the
last section of the page survived.

### Do not use WebFetch for this

Verified 2026-09-04: WebFetch paraphrases the source through its own small model **even under an
explicit "verbatim, do not summarize" instruction** — the real text *"is an end-to-end test
framework"* came back as *"serves as an end-to-end testing framework"*. That fails §2 outright, and
its own description says it processes content through "a small, fast model", so this is a property of
the tool and not of any one site. The extractor route puts no model in the loop at all.

## 2. Quality-check before calling it converted

A conversion that exits 0 is not evidence. Run these:

| Check | How |
|---|---|
| Headings and lists survived structurally, not flattened into one paragraph | read the first screen |
| Tables are still tables, not run-on text — the usual docling/pandoc failure on complex layouts | read one |
| No leftover markup noise: nav bars, cookie banners, JSX source, "Edit this page" | `grep -c "<div\|<header\|<span\|<svg\|<style\|<table\|<img" <dest>.md` → **must be 0** |
| Every link resolves off-site | `grep -oE "\]\(\.{0,2}/?[^):]+\)" <dest>.md` → **must be empty**; a relative target means the URL argument was omitted |
| PDF-to-text: page breaks did not split sentences or merge columns | spot-check two page boundaries. Runs of tabs and spaces between words, and a table of contents rendered as a dot-leader table, are **accepted** (2026-09-18, DDD Reference): they come from the PDF's own text layer, change no meaning, and are not normalised |
| **A `.docx` with diagrams: count the figures** | `grep -c "data:image/[a-z]*;base64" <dest>.md` against the source's *picture* count, `unzip -p <file>.docx word/document.xml \| grep -c "<pic:pic"`. Charts and shapes are counted differently — see below |

**Any hit from the markup grep is a tag pandoc's gfm writer could not map and fell back to raw HTML
for** — the same failure mode as the base64-icon and hash-link cases `extract_article.py` exists to
strip.

**The `.docx` figure rule, measured on docling 2.115.0, 2026-09-20.** Three source files, each
converted twice — with `soffice` on `PATH` and with it removed — gave byte-identical output both
times, so **on this version the LibreOffice round-trip plays no part in a `.docx` conversion** and
there is no `WARNING` to watch for. What each kind of figure becomes:

| In the source | In the markdown |
|---|---|
| `<w:drawing>` holding `pic:pic` (an embedded picture) | a base64 image, read straight from `word/media/` — pixel-identical to the source (`magick compare -metric AE` → 0) |
| A chart (`c:chart`, a `word/charts/chart*.xml` part) | **its data as a pipe table**, plus `<!-- 🖼️❌ Image not available … -->` where the picture would be. `--image-export-mode embedded` does not change this |
| A shape (`wps:wsp`), including grouped shapes | **its text as paragraphs**; the shape itself is not rendered |

So the figure count check compares base64 images against the source's *picture* count, not every
`<w:drawing>`: `unzip -p <file>.docx word/document.xml | grep -o "<pic:pic" | wc -l`. Count the other
two kinds separately — `grep -o "<c:chart" | wc -l` against the tables and the placeholder comments,
and `grep -o "<wps:wsp" | wc -l` against the loose paragraphs. **`grep -c` is wrong here** and
silently answers 1: `word/document.xml` is a single line, so it counts lines, not tags. Evidence: `chartex.docx` (Apache POI test data,
8 drawings = 6 charts + 2 pictures) gave 2 images, 4 placeholders and the chart data as tables;
`shapes-with-text.docx` (11 shapes) gave every shape's text and 1 image; a two-picture document gave
2 of 2. Put
LibreOffice's `program` directory on `PATH` for that one conversion — each figure is a separate
headless round-trip, roughly 100× the conversion time — and do not set `DOCLING_LIBREOFFICE_CMD`,
which docling names in the warning but never reads.

**`<table` is the one with a different remedy.** pandoc's gfm writer cannot put block content — a
list, two paragraphs, several `<br>`-separated links — inside a pipe-table cell, so it emits the whole
table as raw HTML instead. Re-running the JS-hydrated path will not help, because the input was never
the problem. Convert to pandoc's own markdown, which has multiline tables:

```sh
pandoc -f html -t markdown -o "<dest>.md" <tmp>/article.html
```

Measured on rdi.berkeley.edu/llm-agents/f24, a Jekyll syllabus: `-t gfm` gave 377 lines with one raw
`<table>` block; `-t markdown` gave 221 lines, `<table` count 0, all 21 arxiv links and all 13 lecture
rows intact. The cost is that a multiline table is not GFM — it reads as aligned plain text in a viewer
that renders only GFM, rather than as a table.

Any other failure gets re-run through the JS-hydrated path — render with Playwright, extract
with defuddle — even if it was first attempted as a plain fetch. If both fail, flag it for the user
rather than keeping a degraded conversion.

## 3. Post-process embedded images

Conversions from PDF or `.docx` inline figures as base64 data URIs, which bloats the file past the
point any diff or reviewer can work with it:

```sh
python3 <skill>/scripts/clean_md_images.py "<dest>.md"
```

It writes `<dest>-no-base64.md` beside the original and the extracted images into a sibling `<dest>/` folder.
**It never overwrites the original** — check the cleaned file, then replace.

pandoc's `--extract-media` covers the same problem for pandoc's own conversions only; docling output
still needs the script.

## 4. Hand back

Report the route taken, which checks were run, and anything that failed — the caller decides what to
record and where. Do not edit a register, index or catalogue from inside this skill.

## Scripts

All but `render_page.py` are stdlib-only and run under bare `python3` before any venv exists;
`render_page.py` needs `playwright` and runs under the uv tool venv's interpreter. Every test is
stdlib-only — the browser is faked. Tests: `python3 -m unittest discover -s <skill>/tests`.

| Script | Does |
|---|---|
| [`scripts/extract_article.py`](scripts/extract_article.py) | One HTML node out of its page chrome, by `tag`, `tag.class`, `tag#id` or `tag[attr=value]` |
| [`scripts/clean_publisher_md.py`](scripts/clean_publisher_md.py) | A publisher's served markdown into plain GFM — components, anchor-only tags and relative targets out, fenced code untouched |
| [`scripts/add_frontmatter.py`](scripts/add_frontmatter.py) | The corpus frontmatter block onto a converted file — defuddle's metadata where it is installed, the page's own `<title>` and meta tags where it is not |
| [`scripts/clean_md_images.py`](scripts/clean_md_images.py) | base64 data URIs out to sibling PNGs |
| [`scripts/render_page.py`](scripts/render_page.py) | A JS-hydrated page's HTML after hydration, with links made absolute, for defuddle |
