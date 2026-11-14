---
name: fetch-to-markdown
description: Fetch one web page, PDF or Office document and convert it to clean local markdown — classify the source, route it to the right tool (raw README, curl, HTML node extractor plus pandoc, docling, soffice for legacy binary formats, or Playwright plus defuddle), quality-check the result against the original, and strip embedded base64 images. Use when asked to fetch, retrieve, scrape, ingest or convert a docs page, README, PDF, .docx, .doc, .pptx or .ppt into markdown at a given path. Not for general web research — this writes a file.
author: Achilleas Voutsas
version: 0.6.1
---

# Fetch a document to markdown

One source URL, one destination path, clean markdown at the end of it.

**The caller owns the destination.** This skill does not choose the directory, derive the filename, or
record the result anywhere — a project that wants those decisions made for it wraps this skill and
makes them itself. If the request did not name a destination path, ask for one before fetching.

`<skill>` below is this skill's own directory; `<dest>` is the destination path the caller gave.
Commands are written `python`, the interpreter's name on Windows; **on macOS it is `python3`**.

## 1. Classify the source, then route it

| The source is | Route | Command |
|---|---|---|
| `github.com/<owner>/<repo>` | **Raw README only. Never clone.** | `curl -s https://raw.githubusercontent.com/<owner>/<repo>/<branch>/README.md` |
| **A page whose publisher serves its own markdown** — Mintlify (`code.claude.com`, `platform.claude.com`, `modelcontextprotocol.io`), GitHub Docs, Microsoft Learn (`learn.microsoft.com`, by `Accept` header). **Probe for this first**, whatever else the page looks like | `curl <url>.md`, or `curl -H "Accept: text/markdown" <url>` → clean the publisher's components | see below |
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
server-render (evidence: [references/evidence.md](references/evidence.md)). Then:

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
convert with `pandoc -t markdown` (evidence: [references/evidence.md](references/evidence.md)).

**A 404 in a JS app looks exactly like a hydrated page** to the `curl | grep -c` test — both have no
text in the raw HTML. Check the rendered `<title>` before trusting the conversion (evidence: [references/evidence.md](references/evidence.md)).

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
curl -sLI <url>.md | grep -i "^content-type: text/markdown"                          # suffix
curl -sLI -H "Accept: text/markdown" <url> | grep -i "^content-type: text/markdown"  # negotiated
```

**Run both probes.** Publishers expose the source two ways: Mintlify and GitHub Docs at `<url>.md`;
Microsoft Learn only by content negotiation on the page's own URL (evidence: [references/evidence.md](references/evidence.md)).

A hit means the platform serves the page's own markdown source, which is the text itself rather than
a conversion of it — no selector to choose, no pandoc writer to lose a table to, no model anywhere.
Then fetch it the way the probe hit:

```sh
curl -sL <url>.md -o <tmp>/served.md                                 # suffix
curl -sL -H "Accept: text/markdown" <url> -o <tmp>/served.md         # negotiated
curl -sL -A "Mozilla/5.0" <url> -o <tmp>/page.html
python <skill>/scripts/clean_publisher_md.py <tmp>/served.md "<dest>.md" <url>
python <skill>/scripts/add_frontmatter.py "<dest>.md" <tmp>/page.html <url>
```

**Pass the page's own URL, not the site root**, as in the server-rendered route and for the same
reason: root-relative, sibling, parent and bare link targets all resolve against it. A site root alone
leaves the sibling links `modelcontextprotocol.io` writes between its own docs pages pointing at
nothing — the script's docstring spells the four forms out. `add_frontmatter.py` still needs the
rendered HTML, so fetch that too.

**The cleaner removes** publisher component tags, per-IDE wrappers, anchor-only tags, raw lists inside table cells and site-relative link targets. **Fenced code blocks pass through untouched** (evidence: [references/evidence.md](references/evidence.md)).

Two things it cannot fix, both properties of the source rather than the conversion: a code sample the
site itself stores without line breaks comes out on one line whichever route you take, and a relative
link *inside a quoted example file* is correct as it stands. Say so in the hand-back; do not hand-edit
the corpus.

### The server-rendered route

```sh
curl -sL -A "Mozilla/5.0" <url> -o <tmp>/page.html
python <skill>/scripts/extract_article.py <tmp>/page.html <tag|tag.class|tag#id|tag[attr=value]> <url> \
  | pandoc -f html -t gfm -o "<dest>.md"
python <skill>/scripts/add_frontmatter.py "<dest>.md" <tmp>/page.html <url>
```

**Always pass the page's own URL as the third argument.** It resolves relative `href`/`src` targets
against it. Skip it and a link like `./assets/<file>.pdf` converts perfectly and points at nothing —
the markdown is well-formed, so no markup check below can see it.

`extract_article.py` pulls one HTML node by `tag.class`, `tag#id` or `tag[attr=value]` and strips what
pandoc's gfm writer cannot map cleanly — `div`, `header`, `span`, `section`, inline `<svg>`, icon
`<img>`s, `<style>`, empty bookmark anchors — and the chrome that sites put *inside* the article node:
Antora's breadcrumbs and pagination, an "On this page" aside. The source's own text passes through
untouched.

Two more passes (evidence: [references/evidence.md](references/evidence.md)):

- **It writes back end tags the source left out.** Minified pages omit optional end tags, and pandoc then flattens every table cell into its own paragraph. The extractor closes each element where HTML5 implies it.
- **It keeps only `href` and `title` on a link.** pandoc's gfm writer emits a link carrying `target`, `rel` or `id` as raw `<a …>`.

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

A generator's own class name is a shortcut when the page has one, for example Docusaurus's `theme-doc-markdown`. Where it does not, the grep above is the answer (evidence: [references/evidence.md](references/evidence.md)).

**Pick the narrowest node that still holds everything you want.** Too wide drags in nav and footer,
which §2's noise check catches; too narrow silently drops content, which it does not — so confirm the
last section of the page survived.

### Do not use WebFetch for this

WebFetch paraphrases the source through its own small model **even under an explicit "verbatim" instruction**. That fails §2 outright. The extractor route puts no model in the loop at all (evidence: [references/evidence.md](references/evidence.md)).

## 2. Quality-check before calling it converted

A conversion that exits 0 is not evidence. Run these:

| Check | How |
|---|---|
| Headings and lists survived structurally, not flattened into one paragraph | read the first screen |
| Tables are still tables, not run-on text — the usual docling/pandoc failure on complex layouts | read one |
| No leftover markup noise: nav bars, cookie banners, JSX source, "Edit this page" | `grep -c "<div\|<header\|<span\|<svg\|<style\|<table\|<img\|<a " <dest>.md` → **must be 0** |
| Every link resolves off-site | `grep -oE "\]\(\.{0,2}/?[^):]+\)" <dest>.md \| grep -v "^](#"` → **must be empty**; a relative target means the URL argument was omitted. In-page `#` anchors are fine |
| PDF-to-text: page breaks did not split sentences or merge columns | spot-check two page boundaries. Runs of tabs and spaces between words, and a dot-leader table of contents, are **accepted** and not normalised (evidence: [references/evidence.md](references/evidence.md)) |
| **A `.docx` with diagrams: count the figures** | `grep -c "data:image/[a-z]*;base64" <dest>.md` against the source's *picture* count, `unzip -p <file>.docx word/document.xml \| grep -c "<pic:pic"`. Charts and shapes are counted differently — see below |

**Any hit from the markup grep is a tag pandoc's gfm writer could not map and fell back to raw HTML
for** — the same failure mode as the base64-icon and hash-link cases `extract_article.py` exists to
strip.

**The `.docx` figure rule: only a shape needs LibreOffice.** A shape becomes an image only when `soffice` resolves. Without it, docling prints one `WARNING` and exits 0 (evidence: [references/evidence.md](references/evidence.md)). What each kind of figure becomes:

| In the source | In the markdown |
|---|---|
| `<w:drawing>` holding `pic:pic` (an embedded picture) | a base64 image, read straight from `word/media/` — pixel-identical to the source (`magick compare -metric AE` → 0). No LibreOffice needed |
| A chart (`c:chart`, a `word/charts/chart*.xml` part) | **its data as a pipe table**, plus `<!-- 🖼️❌ Image not available … -->` where the picture would be. `--image-export-mode embedded` does not change this, nor does LibreOffice |
| A shape (`wps:wsp`), including grouped shapes | **its text as paragraphs** either way, plus **one rendered image** with `soffice` on `PATH`. Without it, no image — only the `WARNING` |

So the figure count check compares base64 images against the source's *picture* count, not every
`<w:drawing>`: `unzip -p <file>.docx word/document.xml | grep -o "<pic:pic" | wc -l`. Count the other
two kinds separately — `grep -o "<c:chart" | wc -l` against the tables and the placeholder comments,
and `grep -o "<wps:wsp" | wc -l` against the loose paragraphs. **`grep -c` is wrong here** and
silently answers 1: `word/document.xml` is a single line, so it counts lines, not tags (evidence: [references/evidence.md](references/evidence.md)). **When the source has shapes, put LibreOffice's
`program` directory on `PATH` for that one conversion** — each figure is a separate headless
round-trip, roughly 100× the conversion time — and do not set `DOCLING_LIBREOFFICE_CMD`, which docling
names in the warning but never reads.

**`<table` is the one with a different remedy.** pandoc's gfm writer cannot put block content — a
list, two paragraphs, several `<br>`-separated links — inside a pipe-table cell, so it emits the whole
table as raw HTML instead. Re-running the JS-hydrated path will not help, because the input was never
the problem. Convert to pandoc's own markdown, which has multiline tables:

```sh
pandoc -f html -t markdown -o "<dest>.md" <tmp>/article.html
```

`-t markdown` removes the raw `<table>` block (evidence: [references/evidence.md](references/evidence.md)). The cost is that a multiline table is not GFM — it reads as aligned plain text in a viewer
that renders only GFM, rather than as a table.

Any other failure gets re-run through the JS-hydrated path — render with Playwright, extract
with defuddle — even if it was first attempted as a plain fetch. If both fail, flag it for the user
rather than keeping a degraded conversion.

## 3. Post-process embedded images

Conversions from PDF or `.docx` inline figures as base64 data URIs, which bloats the file past the
point any diff or reviewer can work with it:

```sh
python <skill>/scripts/clean_md_images.py "<dest>.md"
```

It writes `<dest>-no-base64.md` beside the original and the extracted images into a sibling `<dest>/` folder.
**It never overwrites the original** — check the cleaned file, then replace.

pandoc's `--extract-media` covers the same problem for pandoc's own conversions only; docling output
still needs the script.

## 4. Hand back

Report the route taken, which checks were run, and anything that failed — the caller decides what to
record and where. Do not edit a register, index or catalogue from inside this skill.

## Scripts

All but `render_page.py` are stdlib-only and run under the bare interpreter before any venv exists,
as `AGENT-INSTRUCTIONS.md` allows for a global skill's scripts; `render_page.py` needs `playwright` and runs under the uv tool venv's interpreter. Every test is
stdlib-only — the browser is faked. Tests, from the project root: `uv run --no-sync python -m unittest discover -s <skill>/tests`.

| Script | Does |
|---|---|
| [`scripts/extract_article.py`](scripts/extract_article.py) | One HTML node out of its page chrome, by `tag`, `tag.class`, `tag#id` or `tag[attr=value]` |
| [`scripts/clean_publisher_md.py`](scripts/clean_publisher_md.py) | A publisher's served markdown into plain GFM — components, anchor-only tags and relative targets out, fenced code untouched |
| [`scripts/add_frontmatter.py`](scripts/add_frontmatter.py) | The corpus frontmatter block onto a converted file — defuddle's metadata where it is installed, the page's own `<title>` and meta tags where it is not |
| [`scripts/clean_md_images.py`](scripts/clean_md_images.py) | base64 data URIs out to sibling PNGs |
| [`scripts/render_page.py`](scripts/render_page.py) | A JS-hydrated page's HTML after hydration, with links made absolute, for defuddle |
