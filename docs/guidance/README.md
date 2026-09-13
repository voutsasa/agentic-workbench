# Guidance — what belongs here

Short, agent-facing notes written to be **loaded mid-task and acted on**. Where `docs/web/` holds material to read, this folder holds conclusions to apply.

Everything here is hand-authored and tracked in git.

## The bar

A note earns a place here when all three hold:

1. **The question recurs.** One-off answers belong in the conversation that asked them, not in a file.
2. **It is shorter than what it replaces.** If reading the guidance costs as much as reading the source, register the source and skip the note.
3. **Its claims are checkable.** Every note declares where its content comes from — see below. Guidance that cannot be traced is an opinion with a filename.

## Declare provenance

State it in the opening lines. Three kinds, in descending order of trust:

| Kind | Evidence required | Example |
|---|---|---|
| **Corpus-derived** | Cite the `SOURCES.md` entry it distils. The register is the source of truth; guidance is a shortcut through it. | *(none yet)* |
| **Workstation-verified** | State what was run and when. Claims about tool behaviour are worthless undated — a broken route gets fixed upstream and the note becomes a lie. | [`pdf-deliverables.md`](pdf-deliverables.md) |

**Corpus-derived is the kind this workbench exists to produce.** That the folder currently holds none is worth noticing rather than smoothing over: it means the distillation half of the workbench has not started, and the register's per-layer gaps are the backlog for starting it.

## What does not belong

- **Source material.** Ingested third-party content goes to `docs/web/`, addressed by the register.
- **Machine description.** How a tool is installed or behaves here goes to `workstation/cli/<tool>/`, or `workstation/mcp/<server>/` for an MCP server. Guidance may *cite* those files, as the PDF note does, but a note that only describes this workstation is misfiled.
- **Per-project artefacts.** Constitutions and skills for a specific project are the workbench's *output*, produced elsewhere from this material.

## Format

- Renders in Zed's plain preview: **no inline HTML, no CSS assets, no render scripts.**
- Tables over prose for anything enumerable — an agent scanning for one row should not read paragraphs.
- Lead with the decision, then the reasoning. A note read under time pressure should be actionable from its first table.
- Assets a note's commands depend on live beside it — `print.css` and `minimal.html` belong to `pdf-deliverables.md`. Reference them by repo-root path so the commands run as written.

## Contents

| File | Kind | What it gives you |
|---|---|---|
| [`pdf-deliverables.md`](pdf-deliverables.md) | workstation-verified | The two adopted PDF routes and how to choose between them. |
| [`print.css`](print.css) | asset | Print stylesheet for the WeasyPrint route. |
| [`minimal.html`](minimal.html) | asset | Pandoc template emitting body HTML without pandoc's own CSS. |
