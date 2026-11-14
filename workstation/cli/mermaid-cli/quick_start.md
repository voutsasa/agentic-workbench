---
tool: mermaid-cli
updated: 2026-08-05
author: Achilleas Voutsas
version: 0.4.0
---

# mermaid-cli — quick start

Renders Mermaid diagram definitions to SVG, PNG or PDF. Unlike the other diagram tools it can read a **markdown file** and render every fenced `mermaid` block it finds, which makes it the one to use for diagrams embedded in documents.

## Render

```
mmdc -i diagram.mmd -o diagram.svg
mmdc -i README.md -o README-out.md        # renders every ```mermaid block
cat diagram.mmd | mmdc -i - -o - > out.svg
```

Output defaults to the input name with `.svg` appended. Input `-` reads stdin; output `-` writes stdout.

## Options

| Option | Effect |
|---|---|
| `-i, --input` | `.mmd` file, `.md` file, or `-` for stdin |
| `-o, --output` | `.md`, `.svg`, `.png`, `.pdf`, or `-` |
| `-e, --outputFormat` | force format when the extension does not imply it |
| `-t, --theme` | `default`, `forest`, `dark`, `neutral` |
| `-b, --backgroundColor` | e.g. `transparent`, `'#F0F0F0'` — PNG and SVG only, not PDF |
| `-w, --width` / `-H, --height` | page size, defaults 800 × 600 |
| `-s, --scale` | Puppeteer scale factor — raise it for legible PNGs |
| `-f, --pdfFit` | scale the PDF page to the diagram |
| `-c, --configFile` / `-C, --cssFile` | mermaid JSON config; custom CSS |
| `-q, --quiet` | suppress log output |

## Traps

- **Markdown input rewrites the file's diagrams.** With a `.md` input and `.md` output, each fenced block is replaced by a link to a generated image — give it a *different* output path unless that is what you want.
- **The default 800 × 600 crops large diagrams.** Set `-w`/`-H` rather than assuming the renderer will fit the content.
- **`--backgroundColor` is ignored for PDF.** Only PNG and SVG honour it.
- **Unlike d2, PNG output works directly** — no `rsvg-convert` hop is needed, provided a browser is reachable.
- **On macOS the Homebrew build has no browser of its own.** Without `PUPPETEER_EXECUTABLE_PATH` every render fails with `Could not find chrome-headless-shell`. Point it at Playwright's Chromium — see [install.md](install.md).

Docs: [README](https://github.com/mermaid-js/mermaid-cli) · full page ingest: [reference.md](reference.md)
