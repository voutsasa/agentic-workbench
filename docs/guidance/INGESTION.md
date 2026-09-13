---
role: Pointer to the ingest-source and fetch-to-markdown skills, which hold the process and the routing
updated: 2026-09-14
verified: never
---

# Ingestion Guide

**The procedure moved into a skill.** It is now
[`skills/ingest-source/SKILL.md`](../../skills/ingest-source/SKILL.md), with the workstation-tooling branch
in [`skills/ingest-source/references/workstation-tooling.md`](../../skills/ingest-source/references/workstation-tooling.md).
The fetching and converting it delegates to — and the two scripts that do it — are in
[`workstation/agent/skills/fetch-to-markdown/`](../../workstation/agent/skills/fetch-to-markdown/),
which is global rather than repo-local.

Read the skill, not this file. Nothing was dropped in the move.

## Why it is a skill and not a guide

A guide is only read by an agent that already knows it exists. A skill's `description` is the
discovery mechanism — it fires on "ingest this source" without anyone having to name the file — and it
carries its scripts and their tests beside the prose that tells you when to run them.

**This file is a pointer rather than a summary, deliberately.** A summary of a procedure is what an
agent reads *instead of* the original, and it is the summary that goes stale. `fix-findings` defers to
`review`'s Apply mode for the same reason.

## What still lives here

Nothing but this pointer. The three facts the rest of the repo asserts about ingestion are stated
where they are enforced, not here:

| Fact | Where |
|---|---|
| One bracket-link entry ↔ one ingested file, named from the bracket text | [`CLAUDE.md`](../../CLAUDE.md) — *Ingestion invariant* |
| The corpus is gitignored and rebuildable, so a fresh clone looks un-ingested and is not | [`CLAUDE.md`](../../CLAUDE.md) — *The corpus is not in git* |
| The user installs and registers; the agent records | [`CLAUDE.md`](../../CLAUDE.md), and applied in the skill's workstation-tooling reference |
