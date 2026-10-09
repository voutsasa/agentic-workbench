---
tool: weasyprint
command: weasyprint
product: WeasyPrint
used_by: pdf-deliverable
verified: 2026-08-20
author: Achilleas Voutsas
version: 0.2.0
---

# weasyprint — install

Binary: `weasyprint`. Product: WeasyPrint. Python tool, but packaged for brew and scoop.

| Platform | Command |
|---|---|
| macOS | `brew install weasyprint` |
| Windows | `scoop install main/weasyprint` |

Verify with `weasyprint --version`; it prints `WeasyPrint version <x.y>`.

## Traps

- **npm `weasyprint` is not this tool.** It is a third-party Node wrapper that shells out to the real Python one. Use the commands above.
- **The brew formula bundles its own Python and native dependencies** (Pango, cairo, GDK-PixBuf). A Python-channel install doesn't bring them. On macOS on 2026-09-27, `uv tool install weasyprint` succeeded, then every run failed with `OSError: cannot load library 'libgobject-2.0-0'`, even with the brew formula's libraries present. That is why this tool stays on brew and scoop.

Docs: [First steps](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) · full page ingest: [reference.md](reference.md)
