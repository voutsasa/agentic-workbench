---
name: fetch-to-markdown
description: Fetch one web page, PDF or Office document and convert it to clean local markdown — classify the source, route it to the right tool (raw README, curl, HTML node extractor plus pandoc, docling, or Playwright plus defuddle), quality-check the result against the original, and strip embedded base64 images. Use when asked to fetch, retrieve, scrape, ingest or convert a docs page, README, PDF or .docx into markdown at a given path. Not for general web research — this writes a file.
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
| A direct `.pdf` | Fetch the file itself, never scrape a rendered viewer | `curl -sL -o "<dest>.pdf" <url>` |
| A local or fetched PDF / Office document | `docling` — real layout understanding, ahead of pandoc | `docling convert <input> --to md --output <dir>` |
| Docusaurus | curl → extract the article node → pandoc | see below |
| A plain server-rendered doc site (Sphinx, ReadTheDocs, MkDocs, VitePress, mdBook, static HTML, classic blogs) | `WebFetch`, then spot-check | see the caveat below |
| A JS-hydrated platform (Mintlify, Fern, Rspress — anything that returned raw JSX under WebFetch) | Playwright → defuddle → pandoc | headless; no browser extension |

**Telling Docusaurus apart:** its theme class names are in the raw HTML — `theme-doc-markdown`,
`docMainContainer_`. Confirmed on playwright.dev, dbml.dbdiagram.io, d2lang.com, drawio.com.

### The Docusaurus route

```sh
curl -sL -A "Mozilla/5.0" <url> -o <tmp>/page.html
python3 <skill>/scripts/extract_article.py <tmp>/page.html div.theme-doc-markdown <url> \
  | pandoc -f html -t gfm -o "<dest>.md"
```

**Always pass the page's own URL as the third argument.** It resolves relative `href`/`src` targets
against it. Skip it and a link like `./assets/<file>.pdf` converts perfectly and points at nothing —
the markdown is well-formed, so no markup check below can see it.

`extract_article.py` pulls one HTML node by `tag.class` or `tag#id` and strips what pandoc's gfm
writer cannot map cleanly — `div`, `header`, `span`, inline `<svg>`, base64 icon `<img>`s, `<style>`,
bookmark `<a name>`s. The source's own text passes through untouched.

**The selector is an argument, so this is not Docusaurus-only.** A hand-rolled layout reuses it with a
different one: plantuml.com's article sits in `<main id="D7">`, so `main#D7` finds it there.

### Do not use WebFetch on Docusaurus

Verified 2026-09-04: WebFetch paraphrases the source through its own small model **even under an
explicit "verbatim, do not summarize" instruction** — the real text *"is an end-to-end test
framework"* came back as *"serves as an end-to-end testing framework"*. That fails §2 outright.

The same risk applies to the plain-doc-site route, because WebFetch's own description says it
processes content through "a small, fast model". It has **not** been checked on
Sphinx/ReadTheDocs/MkDocs/mdBook, so treat it as a per-source caveat rather than a ban: spot-check one
paragraph against the raw HTML before trusting the output.

## 2. Quality-check before calling it converted

A conversion that exits 0 is not evidence. Run these:

| Check | How |
|---|---|
| Headings and lists survived structurally, not flattened into one paragraph | read the first screen |
| Tables are still tables, not run-on text — the usual docling/pandoc failure on complex layouts | read one |
| No leftover markup noise: nav bars, cookie banners, JSX source, "Edit this page" | `grep -c "<div\|<header\|<span\|<svg\|<style\|<table\|<img" <dest>.md` → **must be 0** |
| Every link resolves off-site | `grep -oE "\]\(\.{0,2}/?[^):]+\)" <dest>.md` → **must be empty**; a relative target means the URL argument was omitted |
| PDF-to-text: page breaks did not split sentences or merge columns | spot-check two page boundaries |
| **A `.docx` with diagrams: count the figures** | `grep -c "data:image/[a-z]*;base64" <dest>.md` against the source's figure count |

The `.docx` case is the one that passes every other check while being wrong: **docling drops every
DrawingML figure at exit 0 when `soffice` does not resolve on `PATH`**, so headings and tables come
through perfectly and the images are simply gone. The only signal is one `WARNING` line. Put
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

It writes `<dest>-no-base64.md` beside the original and the PNGs into a sibling `<dest>/` folder.
**It never overwrites the original** — check the cleaned file, then replace.

pandoc's `--extract-media` covers the same problem for pandoc's own conversions only; docling output
still needs the script.

## 4. Hand back

Report the route taken, which checks were run, and anything that failed — the caller decides what to
record and where. Do not edit a register, index or catalogue from inside this skill.

## Scripts

Both are stdlib-only and run under bare `python3` before any venv exists. Tests:
`python3 -m unittest discover -s <skill>/tests`.

| Script | Does |
|---|---|
| [`scripts/extract_article.py`](scripts/extract_article.py) | One HTML node out of its page chrome, by `tag.class` or `tag#id` |
| [`scripts/clean_md_images.py`](scripts/clean_md_images.py) | base64 data URIs out to sibling PNGs |
