---
tool: tesseract
command: tesseract
product: Tesseract OCR
verified: 2026-08-20
author: Achilleas Voutsas
version: 0.2.0
---

# tesseract — install

Binary: `tesseract`. Product: Tesseract OCR.

| Platform | Command |
|---|---|
| macOS | `brew install tesseract` |
| Windows | `scoop install main/tesseract` |

Verify with `tesseract --version`; the first line is `tesseract 5.x.y`, followed by the leptonica version and the image formats it was built against.

## Workstation configuration

**English-only language data — chosen.** The base package ships English only, and the additional packs have not been taken by default. Confirm what a given machine carries with `tesseract --list-langs`; that list is install status and belongs in that machine's file under [`../../machines/`](../../machines/), not here.

This holds because every OCR job here so far has been English. The gap announces itself rather than degrading quietly — `-l deu` or `-l fra` fails with a missing-tessdata error, not poor output. When that happens:

```
brew install tesseract-lang
```

Worth anticipating for EU regulatory documents, which frequently are not in English.

Docs: [Installation](https://tesseract-ocr.github.io/tessdoc/Installation.html) · full page ingest: [reference.md](reference.md)
