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

## SVG input — put rsvg-convert in front, on the build that needs it

```
rsvg-convert diagram.svg | magick png:- -trim +repage diagram.png
```

`magick diagram.svg diagram.png` fails outright with ``unable to read font `'`` on **brew's build**, which is linked against ImageMagick's internal MSVG renderer. This is not specific to one diagram tool — it applies to any SVG carrying embedded fonts, which all three diagram tools produce. `png:-` tells magick the piped stdin is PNG data.

**Which build you are on decides whether you need the hop, and it is a measured fact per machine.** On scoop's Windows build the direct call succeeds: probed 21 September 2026 on ImageMagick 7.1.2-31, a 200×60 SVG carrying a `<text>` element converted at exit 0 to a PNG of the right geometry with 104 distinct grey levels — antialiased glyphs, not a blank canvas — with **no `rsvg-convert` on `PATH` at all**. The delegate table still names `rsvg-convert` for `svg`, so ImageMagick falls back to its own renderer silently rather than failing. Check your own box before adding the hop: `magick x.svg x.png` then `magick identify -format '%wx%h unique=%k' x.png`, and treat `unique=1` as the failure however the exit code reads.

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
