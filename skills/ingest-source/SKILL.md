---
name: ingest-source
description: Pull a source registered in SOURCES.md into this workbench as clean local markdown — classify the page, route it to the right tool (raw README, curl, extractor plus pandoc, or Playwright plus defuddle), quality-check the result, and update SOURCE_CATALOGUE.md. Use when asked to ingest, fetch, re-ingest or convert a registered source, when a bracket-link entry has no file in docs/landing-zone/, or when adding a CLI tool or MCP server to workstation/. Not for general web research — this writes the corpus.
---

# Ingest a source

Turn one `SOURCES.md` entry into clean, reviewable local markdown. **One entry, one file** — the
register is the source of truth and the corpus mirrors it.

> **Ingest only the missing delta.** The corpus is gitignored, so on a fresh clone every entry looks
> un-ingested and it is not. Check for the destination file first; a full re-run is a deliberate,
> expensive operation that happens only when the user asks for it in those words.

## 1. Classify the source, then route it

| The source is | Route | Command |
|---|---|---|
| `github.com/<owner>/<repo>` | **Raw README only. Never clone.** | `curl -s https://raw.githubusercontent.com/<owner>/<repo>/<branch>/README.md` |
| A direct `.pdf` | Fetch the file itself, never scrape a rendered viewer | `curl -sL -o "docs/landing-zone/<topic name>.pdf" <url>` |
| Docusaurus | curl → extract the article node → pandoc | see below |
| A plain server-rendered doc site (Sphinx, ReadTheDocs, MkDocs, VitePress, mdBook, static HTML, classic blogs) | `WebFetch`, then spot-check | see the caveat below |
| A JS-hydrated platform (Mintlify, Fern, Rspress — anything that returned raw JSX under WebFetch) | Playwright → defuddle → pandoc | headless; no browser extension |

**Telling Docusaurus apart:** its theme class names are in the raw HTML — `theme-doc-markdown`,
`docMainContainer_`. Confirmed on playwright.dev, dbml.dbdiagram.io, d2lang.com, drawio.com.

### The Docusaurus route

```sh
curl -sL -A "Mozilla/5.0" <url> -o <tmp>/page.html
python3 skills/ingest-source/scripts/extract_article.py <tmp>/page.html div.theme-doc-markdown \
  | pandoc -f html -t gfm -o "docs/landing-zone/<topic name>.md"
```

`extract_article.py` pulls one HTML node by `tag.class` or `tag#id` and strips what pandoc's gfm
writer cannot map cleanly — `div`, `header`, `span`, inline `<svg>`, base64 icon `<img>`s, `<style>`,
bookmark `<a name>`s. The source's own text passes through untouched.

**The selector is an argument, so this is not Docusaurus-only.** A hand-rolled layout reuses it with a
different one: plantuml.com's article sits in `<main id="D7">`, so `main#D7` finds it there.

### Do not use WebFetch on Docusaurus

Verified 2026-09-04: WebFetch paraphrases the source through its own small model **even under an
explicit "verbatim, do not summarize" instruction** — the real text *"is an end-to-end test
framework"* came back as *"serves as an end-to-end testing framework"*. That fails §3 outright.

The same risk applies to the plain-doc-site route, because WebFetch's own description says it
processes content through "a small, fast model". It has **not** been checked on
Sphinx/ReadTheDocs/MkDocs/mdBook, so treat it as a per-source caveat rather than a ban: spot-check one
paragraph against the raw HTML before trusting the output.

## 2. Where it lands

```
docs/landing-zone/<topic name>.{md,pdf}
```

One flat directory. No per-section subfolders and no per-layer folders — a source can feed more than
one layer, and a physical folder would force a false single home. Layer grouping lives in `SOURCES.md`
alone.

`<topic name>` is **the exact link text between the `[ ]`**, not the repo name, not the page title:
`[Pydantic AI](...)` → `docs/landing-zone/Pydantic AI.md`.

**The one permitted deviation** — a `: ` in the title, the colon *together with the space after it*,
is written as ` - ` in the filename, so the result has single spaces around the dash rather than a
doubled one:

```
[Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl]
  → Understanding Spec-Driven-Development - Kiro, spec-kit, and Tessl.md
```

**One destination exception.** Entries under *Cross-cutting aspects → 2. Workstation tooling* land
beside their authored guidance instead, and carry extra work — read
[`references/workstation-tooling.md`](references/workstation-tooling.md) when, and only when, the entry
sits there:

```
#### CLI tools    → workstation/cli/<topic name>/reference.md
#### MCP servers  → workstation/mcp/<topic name>/reference.md
```

Italic *see also* cross-references are not entries. Every real entry carries exactly one bracket link
with an `http(s)` target, which is what keeps the register-to-corpus mapping one-to-one.

## 3. Quality-check before calling it ingested

A conversion that exits 0 is not evidence. Run these:

| Check | How |
|---|---|
| Headings and lists survived structurally, not flattened into one paragraph | read the first screen |
| Tables are still tables, not run-on text — the usual docling/pandoc failure on complex layouts | read one |
| No leftover markup noise: nav bars, cookie banners, JSX source, "Edit this page" | `grep -c "<div\|<header\|<span\|<svg\|<style" out.md` → **must be 0** |
| PDF-to-text: page breaks did not split sentences or merge columns | spot-check two page boundaries |
| **A `.docx` with diagrams: count the figures** | `grep -c "data:image/[a-z]*;base64" out.md` against the source's figure count |

The `.docx` case is the one that passes every other check while being wrong: **docling drops every
DrawingML figure at exit 0 when LibreOffice is unreachable**, so headings and tables come through
perfectly and the images are simply gone. The opt-in is in
[`workstation/cli/docling/quick_start.md`](../../workstation/cli/docling/quick_start.md#figures-in-a-docx-need-libreoffice-or-they-vanish-silently).

A file that fails any check gets re-run through the JS-hydrated path — render with Playwright, extract
with defuddle — even if it was first attempted as a plain fetch. If both fail, flag it for the user
rather than committing a degraded conversion.

## 4. Post-process embedded images

Conversions from PDF or `.docx` inline figures as base64 data URIs, which bloats the file past the
point any diff or reviewer can work with it:

```sh
python3 skills/ingest-source/scripts/clean_md_images.py "docs/landing-zone/<topic name>.md"
```

It writes `<topic name>-no-base64.md` beside the original and the PNGs into a sibling `<topic name>/`
folder. **It never overwrites the original** — check the cleaned file, then replace.

pandoc's `--extract-media` covers the same problem for pandoc's own conversions only; docling output
still needs the script.

## 5. Record it

Add the source's **one-line, ≤20-word capability summary** to `SOURCE_CATALOGUE.md`, in the same
section and the same position it occupies in `SOURCES.md`. The two files must stay entry-for-entry
identical.

`README.md` is the landing page and carries no source entries, so it needs no change.

For a workstation tooling entry, continue into
[`references/workstation-tooling.md`](references/workstation-tooling.md). Every other entry stops
here — setup instructions are meaningless for a book, a blog post, or a framework's docs.

## Scripts

Both are stdlib-only and run under bare `python3` before any venv exists. Tests:
`python3 -m unittest discover -s skills/ingest-source/tests`.

| Script | Does |
|---|---|
| [`scripts/extract_article.py`](scripts/extract_article.py) | One HTML node out of its page chrome, by `tag.class` or `tag#id` |
| [`scripts/clean_md_images.py`](scripts/clean_md_images.py) | base64 data URIs out to sibling PNGs |
