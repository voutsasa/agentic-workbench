---
tool: weasyprint
command: weasyprint
product: WeasyPrint
verified: 2026-08-20
---

# weasyprint — install

Binary: `weasyprint`. Product: WeasyPrint. Python tool, but packaged for brew and scoop.

| Platform | Command |
|---|---|
| macOS | `brew install weasyprint` |
| Windows | `scoop install main/weasyprint` |

Verify with `weasyprint --version`; it prints `WeasyPrint version 69.x`.

## Traps

- **npm `weasyprint` is not this tool.** It is a third-party Node wrapper that shells out to the real Python one. Use the commands above.
- **The brew formula bundles its own Python and native dependencies** (Pango, cairo, GDK-PixBuf). If you install via `pipx install weasyprint` instead, those system libraries must be present separately or rendering fails at import.

Docs: [First steps](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) · full page ingest: [reference.md](reference.md)
