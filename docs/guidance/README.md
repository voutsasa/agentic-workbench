# Guidance — what belongs here

Short, agent-facing notes written to be **loaded mid-task and acted on**. Where `docs/landing-zone/` holds material to read, this folder holds conclusions to apply.

Everything here is hand-authored and tracked in git.

## The bar

A note earns a place here when all three hold:

1. **The question recurs.** One-off answers belong in the conversation that asked them, not in a file.
2. **It is shorter than what it replaces.** If reading the guidance costs as much as reading the source, register the source and skip the note.
3. **Its claims are checkable.** Every note declares where its content comes from — see below. Guidance that cannot be traced is an opinion with a filename.

## Declare provenance

State it in the opening lines. Two kinds, in descending order of trust:

| Kind | Evidence required | Example |
|---|---|---|
| **Corpus-derived** | Cite the `SOURCES.md` entry it distils. The register is the source of truth; guidance is a shortcut through it. | [`DEVELOPMENT-PLAN.md`](DEVELOPMENT-PLAN.md) |
| **Workstation-verified** | State what was run and when. Claims about tool behaviour are worthless undated — a broken route gets fixed upstream and the note becomes a lie. | *(none — see* Why the PDF note left *below)* |

**Corpus-derived is the kind this workbench exists to produce.** The only one so far is the development plan, which *routes* reading rather than distilling it — worth noticing rather than smoothing over: the distillation half of the workbench has not started, and the register's per-layer gaps are the backlog for starting it.

## Why the PDF note left

It held one note, `pdf-deliverables.md`, and that note is now the global `pdf-deliverable` skill at [`../../workstation/agent/skills/pdf-deliverable/`](../../workstation/agent/skills/pdf-deliverable/).

Two reasons, and the second is the one that generalises:

- **It was workstation-verified, not corpus-derived** — a description of how two CLI tools behave. The *What does not belong* rule below already said machine and tool description is misfiled here.
- **A note is only read by an agent that already knows its filename.** A skill's `description` is the discovery mechanism: it fires on "make me a PDF" with nobody having to remember the file exists. Any note in this folder whose trigger is a *task* rather than a *question* is a skill wearing the wrong hat.

So the bar has a fourth clause in practice: **a note that tells you what to do when you are already doing something is a skill.** What stays here is what you consult while deciding — conclusions distilled from the register, addressed by the layer they inform.

## What does not belong

- **Source material.** Ingested third-party content goes to `docs/landing-zone/`, addressed by the register.
- **Machine description.** How a tool is installed or behaves here goes to `workstation/cli/<tool>/`, or `workstation/mcp/<server>/` for an MCP server. Guidance may *cite* those files, but a note that only describes this workstation is misfiled.
- **Per-project artefacts.** Constitutions and skills for a specific project are the workbench's *output*, produced elsewhere from this material.

## Format

- Renders in Zed's plain preview: **no inline HTML, no CSS assets, no render scripts.**
- Tables over prose for anything enumerable — an agent scanning for one row should not read paragraphs.
- Lead with the decision, then the reasoning. A note read under time pressure should be actionable from its first table.
- Assets a note's commands depend on live beside it, referenced by repo-root path so the commands run as written. A note whose assets have to be reachable from *outside* this repo is a sign it belongs in a skill instead, where they ship with it.

## Contents

| File | Kind | What it gives you |
|---|---|---|
| [`DEVELOPMENT-PLAN.md`](DEVELOPMENT-PLAN.md) | Corpus-derived | Phased curriculum on agentic AI coding, Skills, MCP and SDD, each phase ending in an artefact; ✓/➕ markers make it a prioritised ingestion backlog. |
