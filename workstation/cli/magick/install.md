---
tool: magick
command: magick
product: ImageMagick
verified: 2026-08-20
author: Achilleas Voutsas
version: 0.3.0
---

# magick — install

Binary: `magick`. Product: ImageMagick — note the package name differs from the command.

| Platform | Command |
|---|---|
| macOS | `brew install imagemagick` |
| Windows | `scoop install main/imagemagick` |

Verify with `magick --version`; the first line is `ImageMagick 7.x.y-z` followed by a build string such as `Q16-HDRI aarch64`.

## Workstation configuration

**SVG rasterises through `rsvg-convert` — chosen on macOS.** brew's ImageMagick is built against its internal MSVG renderer, which cannot handle embedded fonts, so `magick file.svg out.png` fails outright there. Rather than rebuild ImageMagick against a different SVG delegate, the macOS workstation installs `librsvg` and puts `rsvg-convert` in front of every SVG-to-raster job. **Scoop's Windows build needs neither** — it rasterises SVG text directly, measured, per [`quick_start.md`](quick_start.md) § *SVG input*, so there is nothing to install on that platform:

```
brew install librsvg
```

This is the standard raster step for the whole diagram toolchain — d2, PlantUML and Mermaid all emit SVG. See [quick_start.md](quick_start.md) for the pipeline.

## Traps

- **The command is `magick`, not `convert`.** ImageMagick 7 folded the old v6 tools into one binary. `convert` may still exist as a deprecated shim, and scripts that rely on it will eventually break.

Docs: [Download](https://imagemagick.org/script/download.php) · full page ingest: [reference.md](reference.md)
