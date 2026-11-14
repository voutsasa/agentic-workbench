---
tool: pandoc
command: pandoc
product: Pandoc
used_by: fetch-to-markdown, pdf-deliverable
verified: 2026-08-20
author: Achilleas Voutsas
version: 0.4.2
---

# pandoc — install

Binary: `pandoc`. Product: Pandoc. Self-contained Haskell binary; no runtime dependency for markup-to-markup conversion.

| Platform | Command |
|---|---|
| macOS | `brew install pandoc` |
| Windows | `scoop install main/pandoc` |

Verify with `pandoc --version`; the first line is `pandoc 3.x.y`, followed by the data directory and the user data directory it will read.

## Workstation configuration

**No LaTeX — chosen.** Pandoc does not render PDF itself; it shells out to an external engine and defaults to LaTeX. No LaTeX toolchain is installed here and none will be: MacTeX is roughly 5 GB, BasicTeX around 500 MB, and nothing in this repo needs LaTeX-specific typesetting. The cost is that `pandoc input.md -o output.pdf` fails with `'pdflatex' not found`.

Two engines are present, both tested 1 August 2026:

| Engine | Result |
|---|---|
| `--pdf-engine=typst` | works — produced a valid PDF from markdown |
| `--pdf-engine=weasyprint` | fails — pandoc's default HTML template emits CSS WeasyPrint rejects |

**The adopted routes:**

1. **Markdown to PDF — `--pdf-engine=typst`, always named explicitly.** There is no working default, so the flag is not optional.
2. **Anything with a required page format — skip pandoc, drive `weasyprint` directly** from HTML and CSS you control. See [`weasyprint`](../weasyprint/quick_start.md).

Installing LaTeX would silently re-enable pandoc's default and produce different output from route 1. If a genuine LaTeX need appears, raise it rather than installing it quietly.

Docs: [Installing pandoc](https://pandoc.org/installing.html) · full page ingest: [reference.md](reference.md)
