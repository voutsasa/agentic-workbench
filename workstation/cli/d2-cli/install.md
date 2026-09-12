---
tool: d2-cli
command: d2
product: D2 (Terrastruct)
verified: 2026-08-20
---

# d2-cli — install

Binary: `d2`. Product: D2 (Terrastruct). Self-contained Go binary — no runtime dependency for SVG output.

| Platform | Command |
|---|---|
| macOS | `brew install d2` |
| Windows | `scoop install main/d2` |

Verify with `d2 --version`; it prints `v0.x.y-HEAD`. **The `-HEAD` suffix is not a development build.** The binary appends it to its own version string while Homebrew reports the same release without it, so the two disagree on spelling rather than on version — do not chase the difference.

**Windows, 24 August 2026: `v0.7.1`** — a stale scoop install, one minor version behind this page and
behind brew stable. `scoop update d2` clears it; not run, as version currency is the user's call.

PNG output needs `librsvg` as well — `brew install librsvg` — because d2's own raster path is broken. See [quick_start.md](quick_start.md).

On Windows the `librsvg` dependency is **unverified**. `magick` here is scoop's build, not brew's, so
the MSVG-renderer failure that forces the `rsvg-convert` hop on macOS may not apply. Test before
assuming either way.

## Traps

- **Ignore the `curl … | sh` script the docs lead with.** It does not verify release signatures, and both packaged routes above are current.
- **Do not cross ecosystems by name.** PyPI `d2` (`okanakbulut/d2`, 0.8.1) and npm `d2` (DHIS2's JavaScript client, 31.10.2) both look actively maintained. Neither is Terrastruct's diagram language.

Docs: [Install](https://d2lang.com/tour/install/) · full page ingest: [reference.md](reference.md)
