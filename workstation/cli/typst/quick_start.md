---
tool: typst
updated: 2026-09-18
author: Achilleas Voutsas
version: 0.3.0
---

# typst — quick start

Markup-based typesetting system that compiles `.typ` sources to PDF. Here it is mainly the PDF engine
behind `pandoc`; use it directly when you need to adjust the generated Typst before rendering.

## Through pandoc — the usual route

```
pandoc input.md --pdf-engine=typst -o output.pdf
```

Name the engine every time: pandoc's default is LaTeX, which this workstation does not have. See
[`../pandoc/quick_start.md`](../pandoc/quick_start.md).

## Directly

```
pandoc input.md -t typst -o input.typ     # markdown to Typst source, to inspect or edit
typst compile input.typ output.pdf        # render it
typst watch input.typ                     # re-render on every save
```

Both routes were run on macOS on 2026-09-18 with pandoc 3.11 and typst 0.15.1, and each produced a
one-page PDF from a markdown file carrying a heading, bold text and a table.

## Flags and subcommands worth knowing

| Command | Effect |
|---|---|
| `typst compile in.typ out.png` | PNG or SVG output; a multi-page document needs a `{p}` page-number template in the output name |
| `--root DIR` | project root; files outside it cannot be read by the document |
| `--font-path DIR` | extra font directory |
| `typst fonts` | list the fonts Typst can see — the first check when a font falls back silently |

## Traps

- **Typst is not LaTeX.** `biblatex` styles, `header-includes` packages and LaTeX float control do not
  carry over through pandoc.
- **A layout-controlled deliverable goes through `weasyprint`, not here.** See the `pdf-deliverable`
  skill and [`../weasyprint/quick_start.md`](../weasyprint/quick_start.md).

Docs: [typst/typst](https://github.com/typst/typst) · full page ingest: [reference.md](reference.md)
