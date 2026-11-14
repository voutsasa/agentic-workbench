---
tool: poppler
updated: 2026-10-29
author: Achilleas Voutsas
version: 0.4.2
---

# poppler — quick start

PDF to text, with or without positions. Reach for it when a PDF's layout carries meaning (table
cells, columns, fonts) and you parse it in code. For structured markdown of a whole document,
`docling` is the better route.

## Commands

```
pdftotext -layout in.pdf out.txt       # plain text, keeping the columns' layout
pdftotext -f 3 -l 5 in.pdf -           # pages 3 to 5, to stdout
pdftohtml -xml -i -q -stdout in.pdf    # every text run with its position and font, as XML
pdfinfo in.pdf                         # pages, producer, metadata
```

## Traps

- **The version changes the output.** Line placement in `pdftohtml -xml` differs between releases;
  a parser tuned to one can lose text on another. See [install.md](install.md) for the floor.
- **`-i` drops images**, which is what you want for text; without it `pdftohtml` writes image files
  next to the output.
- **The XML is UTF-8 but may hold control characters** that are not valid XML; strip them before
  parsing.

Docs: [Poppler](https://poppler.freedesktop.org/)
