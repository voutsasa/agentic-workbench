---
tool: magick
command: magick
updated: 2026-08-01
---

# magick — quick start

Image conversion, cropping, scaling, and format changes. In this workbench it is mostly the **raster step at the end of a diagram pipeline** — d2, PlantUML and Mermaid all emit SVG, and `magick` turns that into PNG.

## Convert and tidy

```
magick input.png -trim +repage output.png
magick input.png -resize 50% output.jpg
```

`-trim` removes uniform border; `+repage` discards the offset `-trim` leaves behind. Omitting `+repage` is the usual cause of a PNG that looks correct but positions wrongly when embedded.

## SVG input — put rsvg-convert in front

```
rsvg-convert diagram.svg | magick png:- -trim +repage diagram.png
```

`magick diagram.svg diagram.png` fails outright with ``unable to read font `'`` on this workstation. This is not specific to one diagram tool — it applies to any SVG carrying embedded fonts, which all three diagram tools produce. `png:-` tells magick the piped stdin is PNG data.

## Operations worth knowing

| Operation | Effect |
|---|---|
| `-trim` / `+repage` | crop uniform border, then reset the virtual canvas |
| `-resize 800x600` / `-resize 50%` | scale, preserving aspect ratio |
| `-density N` | input resolution for vector and PDF sources; set it *before* the input file |
| `-background white -alpha remove` | flatten transparency, avoiding black backgrounds in JPEG |
| `-quality N` | JPEG/PNG compression level |
| `magick identify file` | report dimensions, format, colour depth without converting |

## Trap

**`-density` must precede the input filename.** It configures how the input is rasterised, so `magick -density 300 in.pdf out.png` works and `magick in.pdf -density 300 out.png` silently gives you a low-resolution image.

Docs: [Command-line processing](https://imagemagick.org/script/command-line-processing.php) · full page ingest: [reference.md](reference.md)
