---
tool: plantuml-cli
updated: 2026-08-05
author: Achilleas Voutsas
version: 0.4.2
---

# plantuml-cli — quick start

UML and architecture diagrams from plain text — component, sequence, class, state, deployment. The register lists it under solution architecture for exactly that: C4-style component views as diffable source.

## Render

```
plantuml --svg diagram.puml
plantuml --format svg --output-dir out/ "diagrams/**/*.puml"
cat diagram.puml | plantuml --svg -pipe > out.svg
```

Output lands next to the input unless `--output-dir` says otherwise. **PNG is the default format** — pass `--svg` explicitly if you want vector output, which is what this workbench prefers.

## Formats and options

| Option | Effect |
|---|---|
| `--svg` / `--png` / `--eps` | output format; `--format <name>` also takes `pdf`, `latex` |
| `--txt` / `--utxt` | ASCII art, Unicode variant — useful for terminal output |
| `-p`, `--pipe` | read stdin, write stdout |
| `-o`, `--output-dir` | write elsewhere than alongside the source |
| `-d, --define VAR=value` | set a preprocessing variable |
| `--dark-mode` | render dark |
| `--check-graphviz` | verify the Graphviz dependency |
| `--skip-fresh` | skip outputs already up to date |
| `--extract-source` | recover the PlantUML source embedded in a generated PNG or SVG |

Accepts files, directories, or glob patterns. `**` recurses — **quote the pattern** (`"**/*.puml"`) or the shell expands it first.

## Traps

- **A rendering failure is usually Graphviz, not your syntax.** Run `plantuml --check-graphviz` before debugging the diagram. See [install.md](install.md).
- **Embedding tools do not use this wrapper.** md2conf and similar look for `java` plus a `plantuml.jar`, never for a `plantuml` executable, so they need `PLANTUML_CMD='plantuml'` in `~/.zshenv` — see [install.md](install.md).
- **`--extract-source` recovers lost sources.** PlantUML embeds the source in image metadata, so a diagram whose `.puml` went missing is not lost.
- **For PNG, prefer rendering SVG then rasterising** with `magick`, as with the other diagram tools — it gives control over scale and trimming that PlantUML's own PNG output does not. Put `rsvg-convert` in front only on a build that needs it: [`../magick/quick_start.md`](../magick/quick_start.md) § *SVG input*.

Docs: [Starting with PlantUML](https://plantuml.com/starting) · full page ingest: [reference.md](reference.md)
