---
name: ingest-source
description: Pull a source registered in SOURCES.md into this workbench — resolve where the entry lands and what it is named, fetch and convert it with the fetch-to-markdown skill, then record it in SOURCE_CATALOGUE.md. Use when asked to ingest, re-ingest or convert a registered source, when a bracket-link entry has no file in docs/landing-zone/, or when adding a CLI tool or MCP server to workstation/. Not for general web research — this writes the corpus.
---

# Ingest a source

Turn one `SOURCES.md` entry into clean, reviewable local markdown. **One entry, one file** — the
register is the source of truth and the corpus mirrors it.

> **Ingest only the missing delta.** The corpus is gitignored, so on a fresh clone every entry looks
> un-ingested and it is not. Check for the destination file first; a full re-run is a deliberate,
> expensive operation that happens only when the user asks for it in those words.

This skill owns the register: where an entry lands, what the file is called, and what gets written
back. **The fetching and converting belong to the global `fetch-to-markdown` skill** —
classify the page, route it, quality-check the result, strip base64 images. Resolve the destination
below first, then invoke that skill with the URL and the resolved path.

## 1. Where it lands

```
docs/landing-zone/<topic name>.{md,pdf}
```

One flat directory. No per-section subfolders and no per-layer folders — a source can feed more than
one layer, and a physical folder would force a false single home. Layer grouping lives in `SOURCES.md`
alone.

`<topic name>` is **the exact link text between the `[ ]`**, not the repo name, not the page title:
`[Pydantic AI](...)` → `docs/landing-zone/Pydantic AI.md`.

**The one permitted deviation** — a `: ` in the title, the colon *together with the space after it*,
is written as ` - ` in the filename, so the result has single spaces around the dash rather than a
doubled one:

```
[Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl]
  → Understanding Spec-Driven-Development - Kiro, spec-kit, and Tessl.md
```

**One destination exception.** Entries under *Cross-cutting aspects → 2. Workstation tooling* land
beside their authored guidance instead, and carry extra work — read
[`references/workstation-tooling.md`](references/workstation-tooling.md) when, and only when, the entry
sits there:

```
#### CLI tools    → workstation/cli/<topic name>/reference.md
#### MCP servers  → workstation/mcp/<topic name>/reference.md
```

Italic *see also* cross-references are not entries. Every real entry carries exactly one bracket link
with an `http(s)` target, which is what keeps the register-to-corpus mapping one-to-one.

## 2. Fetch and convert

Hand the entry's URL and the path resolved above to
the global `fetch-to-markdown` skill. It classifies the source, picks the route, runs
the quality checks and cleans embedded images. Do not re-derive any of that here.

Its checks are pass/fail, and a failure it flags is **not** ingested: re-run or raise it with the user
rather than recording a degraded conversion.

## 3. Record it

Add the source's **one-line, ≤20-word capability summary** to `SOURCE_CATALOGUE.md`, in the same
section and the same position it occupies in `SOURCES.md`. The two files must stay entry-for-entry
identical.

`README.md` is the landing page and carries no source entries, so it needs no change.

For a workstation tooling entry, continue into
[`references/workstation-tooling.md`](references/workstation-tooling.md). Every other entry stops
here — setup instructions are meaningless for a book, a blog post, or a framework's docs.
