---
role: Open work carried between sessions — what is unproven, not what is unwritten
updated: 2026-09-13
verified: never
---

# TODO

Work that is known-outstanding rather than merely imagined. Each item says what would close it, so a
cold session can act without reconstructing the reasoning.

**An item earns a place here only if it is unproven, not if it is unwritten.** An idea nobody has
committed to belongs in a conversation; a gap that a run would close belongs here. Delete an item when
its evidence exists — a passing command, a converted file — and not when it merely feels handled.

## Open

### 1. `ingest-source` has never run end-to-end

Opened 2026-09-13, when `fetch-to-markdown` was split out of it.

The skill is loadable in this clone now, but nothing has exercised what it kept: deriving the filename
from the bracket text, the `: ` → ` - ` rule, the *Cross-cutting aspects → 2. Workstation tooling*
destination exception, and the `SOURCE_CATALOGUE.md` write-back.

**Closes when:** one real `SOURCES.md` entry is ingested through the skill and lands at the right path
with a matching catalogue line — ideally an entry whose title carries a colon, since that is the rule
most likely to be got wrong.

### 2. `fetch-to-markdown` has one route proven of five

Opened 2026-09-13. Server-rendered HTML is proven against rdi.berkeley.edu/llm-agents/f24 — that run
is what found the `<table>` and relative-link defects the skill now guards against.

| Route | State |
|---|---|
| Server-rendered HTML → extractor → pandoc | **proven** |
| `github.com/<owner>/<repo>` → raw README | unproven |
| Direct `.pdf` → curl | unproven |
| PDF / Office → docling | unproven, and the `.docx` figure trap is the one that passes every check while being wrong |
| JS-hydrated → Playwright → defuddle | unproven |

**Closes when:** each route has converted one real source and passed §2's checks. The `.docx` case
needs a file that actually contains DrawingML figures, or it proves nothing.

### 3. The `-t markdown` fallback does not render in Zed

Opened 2026-09-13, with the fallback itself.

A page whose tables hold block content converts to pandoc multiline tables, which are plain text but
not GFM — so Zed's plain preview shows them aligned rather than ruled. That contradicts *Markdown
deliverables must render in Zed's plain preview* in the global instructions.

It is currently harmless: the fallback only fires on ingested corpus files, which are read as sources
rather than handed over. **Closes when** either an ingested page has to become a deliverable — at
which point the answer is probably to split the table rather than to change the writer — or the
constraint is written down as applying to authored documents only.

## Closed

Nothing yet. An item moves here with the evidence that closed it, or is deleted outright; a list of
things that turned out fine is not worth carrying.
