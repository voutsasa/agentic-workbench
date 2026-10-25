---
tool: docling
updated: 2026-08-26
author: Achilleas Voutsas
version: 0.3.0
---

# docling — quick start

PDF and Office documents into structured markdown, with real layout understanding — reading order, table structure, headings, formulas. **This is the first choice for PDF and `.docx` ingestion**, ahead of pandoc, which flattens complex layouts.

## Convert

```
docling convert input.pdf --to md --output docs/landing-zone/
```

Accepts a local path or a URL. Output goes to a *directory*, not a filename; docling names the file after the input.

docling exposes `convert` and `convert-remote` subcommands. The project README still shows the older bare form (`docling <source>`), which continues to work — prefer the subcommand. Which version is installed on a given machine is in [`../../machines/`](../../machines/).

## Options worth knowing

| Option | Effect |
|---|---|
| `--from` / `--to` | input and output format; `--to md`, `html`, `json`, `doctags` |
| `--ocr` / `--no-ocr` | OCR on scanned pages; `--force-ocr` re-OCRs even extractable text |
| `--ocr-engine` / `--ocr-lang` | pick the OCR backend and its languages |
| `--table-mode` | table-structure model accuracy against speed |
| `--image-export-mode` | how figures are emitted — referenced, embedded, or dropped |
| `--pipeline vlm` | vision-language model route, e.g. `--vlm-model granite_docling` |
| `--enrich-code`, `--enrich-formula`, `--enrich-picture-*` | optional per-element enrichment passes, off by default |
| `--device`, `--num-threads` | compute placement and parallelism |

## Shapes in a `.docx` need LibreOffice, or their images vanish silently

A `.docx` carrying DrawingML shapes — diagrams, drawn shapes, grouped shapes — converts **at exit 0 with
every shape's image dropped** unless `soffice` resolves on `PATH`; the text in them survives, and
embedded pictures and chart data need no LibreOffice at all. The only signal is one `WARNING` line in the
log, so **check the image count, not the exit code**:

```powershell
(Select-String -Path out.md -Pattern "data:image/[a-z]+;base64" -AllMatches).Matches.Count
```

Opt in for the conversion that needs figures, and only that one — each figure is a separate headless
LibreOffice round-trip, measured at roughly **100× the conversion time** (3.45 s → 356.62 s on one file
with 14 figures):

```powershell
$env:PATH = "$HOME\scoop\apps\libreoffice\current\LibreOffice\program;" + $env:PATH
```

Process-scoped, so it lasts for that shell only. **Do not set `DOCLING_LIBREOFFICE_CMD`** — docling names
it in the warning it prints but never reads it. Evidence, the `.com`-not-`.exe` trap, and the install
route are in [`install.md`](install.md#embedded-images-need-libreoffice).

`--image-export-mode` is a different knob: it decides *how* a figure is emitted once docling has one. With
no LibreOffice there is nothing to emit in any mode.

## After converting

Docling inlines figures as base64 data URIs, which bloats the file and makes it unreadable. Run the repo's cleaner:

```
uv run --no-sync python workstation/agent/skills/fetch-to-markdown/scripts/clean_md_images.py "docs/landing-zone/<topic name>.md"
```

It writes `<topic name>-no-base64.md` plus a sibling folder of PNGs. Check it, then replace the original. `--image-export-mode` can avoid the problem at source, but the cleaner is the established route here.

Docs: [Usage](https://docling-project.github.io/docling/usage/) · full page ingest: [reference.md](reference.md)
