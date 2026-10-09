---
tool: d2-cli
updated: 2026-08-01
author: Achilleas Voutsas
version: 0.2.0
---

# d2-cli — quick start

Diagrams as text: a `.d2` source file compiles to SVG with automatic layout. Output defaults to SVG when no output path is given.

## Render

```
d2 --scale 2 input.d2 out.svg
```

`--scale` sets render resolution. The default, `-1`, makes SVGs fit to screen; `1` turns fitting off.

## PNG — never ask d2 directly

`d2 input.d2 out.png` fails outright on 0.7.1. PNG, PDF, GIF and PPTX all shell out to a bundled Playwright driver (1.47.2) fetched from `playwright*.azureedge.net`, and those URLs now return 404 on all three mirrors. It does not fall back; no file is written.

Render SVG, then rasterise separately:

```
d2 --scale 2 input.d2 out.svg
rsvg-convert out.svg | magick png:- -trim +repage out.png
```

**Whether the `rsvg-convert` hop is optional is a measured, per-machine fact, not a rule** — see
[`../magick/quick_start.md`](../magick/quick_start.md) § *SVG input*. On brew's macOS build,
``magick out.svg out.png`` fails outright with ``unable to read font `'`` — brew's ImageMagick is built
against its internal MSVG renderer, which cannot handle the fonts d2 embeds — so the hop is not
optional there. On this workbench's scoop Windows build, `magick` converts a d2-generated SVG (with
its embedded fonts) directly to a non-blank PNG at exit 0, with no `rsvg-convert` on `PATH` at all —
measured 29 September 2026, recorded in [`../../machines/windows-ema-pf5n4xe7.md`](../../machines/windows-ema-pf5n4xe7.md).
Check your own build with the test in `magick/quick_start.md` before assuming either way; see
[`install.md`](install.md) for the platform split.

## Capabilities

| Command | Use |
|---|---|
| `d2 in.d2 out.svg` | compile and render |
| `d2 -w in.d2 out.svg` | watch mode — opens a browser that live-reloads on save |
| `d2 validate in.d2` | check the source compiles |
| `d2 fmt in.d2` | format source in place; `--check` verifies without writing |
| `d2 layout` | list layout engines; `d2 layout elk` for its options |
| `d2 themes` | list theme IDs for `--theme` |

## Flags worth knowing

| Flag | Effect |
|---|---|
| `--layout elk` | swap dagre (default) for ELK's layered algorithm |
| `--theme N` / `--dark-theme N` | theme ID; dark defaults to the light one unless set |
| `--pad N` | padding in pixels around the diagram (default 100) |
| `--sketch` | hand-drawn rendering style |
| `--timeout N` | seconds before giving up (default 120) — raise it for large diagrams |
| `--no-xml-tag` | drop the XML declaration when embedding the SVG in HTML |

Both bundled layout engines are `dagre` and `elk`; there are no others without a plugin.

Docs: [Hello world](https://d2lang.com/tour/hello-world/) · full page ingest: [reference.md](reference.md)
