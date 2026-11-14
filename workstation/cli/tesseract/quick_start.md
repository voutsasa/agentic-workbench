---
tool: tesseract
updated: 2026-08-01
author: Achilleas Voutsas
version: 0.4.0
---

# tesseract — quick start

OCR: text out of images and scanned pages. Reach for it only when a document has **no text layer** — for scanned PDFs, `docling convert --ocr` is the better route because it keeps layout and table structure, which raw tesseract discards.

## Extract text

```
tesseract input.png output          # writes output.txt
tesseract input.png output -l eng   # explicit language
tesseract input.png -               # write to stdout
```

The second argument is an output *base name*, not a filename — tesseract appends the extension itself. `tesseract in.png out.txt` produces `out.txt.txt`.

## Options

| Option | Effect |
|---|---|
| `-l LANG[+LANG]` | OCR language(s); combine with `+`, e.g. `-l eng+deu` |
| `--list-langs` | show what language data is actually installed |
| `--psm N` | page segmentation mode — how the page is carved into text regions |
| `--oem N` | OCR engine mode |
| `--help-extra` | the advanced option list |

`-l` and other OCR options must come **before** any configfile argument.

## Traps

- **English-only by default.** See [install.md](install.md) — other languages need `tesseract-lang`.
- **Page segmentation mode matters more than it looks.** The default assumes a full page of text. For a single line, a column, or a cropped label, the default `--psm` returns empty or garbled output; try `--psm 6` (uniform block) or `--psm 7` (single line) before concluding the image is unreadable.
- **Pre-process first.** Deskewing, upscaling, and raising contrast with `magick` usually helps more than any tesseract flag.

Docs: [Command-line usage](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html) · full page ingest: [reference.md](reference.md)
