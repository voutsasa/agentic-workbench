---
name: ingest-source
description: Pull a source registered in SOURCES.md into this workbench — resolve where the entry lands and what it is named, fetch and convert it with the fetch-to-markdown skill, then record it in SOURCE_CATALOGUE.md. Use when asked to ingest, re-ingest or convert a registered source, when a bracket-link entry has no file in docs/landing-zone/, or when adding a CLI tool or MCP server to workstation/. Not for general web research — this writes the corpus.
author: Achilleas Voutsas
version: 0.4.0
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

The destination rule — path, filename, the ` - ` for a `: `, and the workstation-tooling exception — is
stated once, in [`SOURCES.md` § *Conventions*](../../SOURCES.md#conventions), *Ingestion invariant*.
Don't apply it by hand: `repo_check.py --corpus` prints the resolved destination of every entry not
yet ingested, so read this entry's line there — an entry it does not list is already on disk:

```
python workstation/agent/skills/review/scripts/repo_check.py --corpus
```

The name is the link text between the `[ ]`, never the repo name or page title. `docs/landing-zone/`
is one flat directory, because a source can feed more than one layer; layer grouping lives in
`SOURCES.md` alone.

When the entry sits under *Cross-cutting aspects → 2. Workstation tooling*, it also carries extra work:
read [`references/workstation-tooling.md`](references/workstation-tooling.md) then, and only then.

## 2. Fetch and convert

Hand the entry's URL and the path resolved above to
the global `fetch-to-markdown` skill. It classifies the source, picks the route, runs
the quality checks and cleans embedded images. Do not re-derive any of that here.

Its checks are pass/fail, and a failure it flags is **not** ingested: re-run or raise it with the user
rather than recording a degraded conversion.

## 3. Record it

Confirm the source's **one-line, ≤20-word capability summary** already exists in
`SOURCE_CATALOGUE.md`, in the same section and position it occupies in `SOURCES.md` — `AGENTS.md` has
it written together with the `SOURCES.md` change at registration. Add it only if the entry was
registered without one. The two files must stay entry-for-entry identical.

`README.md` is the landing page and carries no source entries, so it needs no change.

For a workstation tooling entry, continue into
[`references/workstation-tooling.md`](references/workstation-tooling.md). Every other entry stops
here — setup instructions are meaningless for a book, a blog post, or a framework's docs.
