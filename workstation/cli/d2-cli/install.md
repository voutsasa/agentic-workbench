---
tool: d2-cli
command: d2
product: D2 (Terrastruct)
verified: 2026-08-20
author: Achilleas Voutsas
version: 0.4.1
---

# d2-cli — install

Binary: `d2`. Product: D2 (Terrastruct). Self-contained Go binary — no runtime dependency for SVG output.

| Platform | Command |
|---|---|
| macOS | `brew install d2` |
| Windows | `scoop install main/d2` |

Verify with `d2 --version`; it prints `v0.x.y-HEAD`. **The `-HEAD` suffix is not a development build.** The binary appends it to its own version string while Homebrew reports the same release without it, so the two disagree on spelling rather than on version — do not chase the difference.

A local install can lag its channel; `scoop update d2` clears it. Whether a given machine is behind is
install status, so it belongs in that machine's file under [`../../machines/`](../../machines/), not
here — and acting on it is the user's call either way.

PNG output needs `librsvg` as well — `brew install librsvg` — because d2's own raster path is broken. See [quick_start.md](quick_start.md).

On Windows the `librsvg` dependency **does not apply to the `magick` hop**, tested 21 September 2026:
scoop's ImageMagick build converts an SVG carrying text directly, with no `rsvg-convert` on `PATH` —
the evidence is in [`../magick/quick_start.md`](../magick/quick_start.md) § *SVG input*. d2's own raster
path is a separate question and is still untested here.

## Traps

- **Ignore the `curl … | sh` script the docs lead with.** It does not verify release signatures, and both packaged routes above are current.
- **Do not cross ecosystems by name.** PyPI `d2` (`okanakbulut/d2`, 0.8.1) and npm `d2` (DHIS2's JavaScript client, 31.10.2) both look actively maintained. Neither is Terrastruct's diagram language.

Docs: [Install](https://d2lang.com/tour/install/) · full page ingest: [reference.md](reference.md)
