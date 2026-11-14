---
tool: poppler
command: pdftohtml
version_flag: -v
product: Poppler
verified: 2026-10-29
author: Achilleas Voutsas
version: 0.4.2
---

# poppler — install

Binaries: `pdftohtml`, `pdftotext`, `pdfinfo` and the other `pdf*` utilities. Product: Poppler.

| Platform | Command |
|---|---|
| macOS | `brew install poppler` |
| Windows | `scoop install main/poppler` |

Verify with `pdftohtml -v`; the first line is `pdftohtml version 26.x.y`. On 2026-10-29 Homebrew
had 26.10.0 and Scoop's Main bucket 26.09.0-0 (`bucket/poppler.json`, a build from
`oschwartz10612/poppler-windows`).

## Version floor

**26.01 or later.** ea-data-model's extractor reads EMA PDFs with `pdftohtml -xml` and refuses an
older poppler (`POPPLER_MIN` in `glossary/__main__.py`). 25.07, the version in Azure Linux 4.0,
misplaces text lines and loses definitions; 25.03 and 26.01 give the same output as 26.10.

Docs: [Poppler](https://poppler.freedesktop.org/)
