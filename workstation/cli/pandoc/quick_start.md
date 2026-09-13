---
tool: pandoc
command: pandoc
updated: 2026-08-01
---

# pandoc — quick start

Universal document converter: 51 input formats, 76 output formats. The general-purpose fallback when a format pair has no specialist tool. For PDF and Office documents *into* markdown, reach for `docling` first — it preserves structure far better.

## Convert

```
pandoc input.docx -o output.md
pandoc input.html -t gfm -o output.md
```

Format is inferred from the file extension. Override with `-f` (from) and `-t` (to) when the extension lies or you are piping.

## PDF — you must name an engine

```
pandoc input.md --pdf-engine=typst -o output.pdf
```

Plain `pandoc input.md -o output.pdf` fails with ``'pdflatex' not found``. **This workstation deliberately has no LaTeX**, and pandoc defaults to it, so naming `typst` is not optional — see [install.md](install.md).

Two consequences worth knowing before you rely on this:

- **Typst is not LaTeX.** Anything expecting LaTeX-specific behaviour — `biblatex` citation styles, packages pulled in via `header-includes`, fine-grained float placement — will not carry over. Plain prose, headings, tables and basic math are fine.
- **For layout you actually control, skip pandoc entirely.** Write the HTML and CSS and drive [`weasyprint`](../weasyprint/quick_start.md) directly. That is the adopted route for any deliverable with a required page format, which pandoc's template is not designed to give you.

## Flags worth knowing

| Flag | Effect |
|---|---|
| `-f` / `-t` | input and output format, overriding extension inference |
| `-s` | standalone — emit a full document with header, not a fragment |
| `--extract-media=DIR` | pull embedded images out to a directory instead of inlining them |
| `--wrap=none` | one line per paragraph; easier to diff |
| `--toc` | generate a table of contents |
| `-o -` | write to stdout |

`--list-input-formats` and `--list-output-formats` enumerate what is available.

## Note

`--extract-media` covers the same problem as [`clean_md_images.py`](../../agent/skills/fetch-to-markdown/scripts/clean_md_images.py) but only for pandoc's own conversions. Docling output still needs the script.

Docs: [Getting started](https://pandoc.org/getting-started.html) · full page ingest: [reference.md](reference.md)
