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

### 4. `setup-agents` has never run end-to-end

Opened 2026-09-13, with the skill.

What is proven is its parts: `detect.py` ran on the macOS workstation and reported what is there, and
`link_config.py --agent copilot` and `--project` both reached *N of N linked* here. The flow that joins
them has not run — the questions in step 2, the change table built from `link_config.py --json` in
step 3, and either mode of step 4. A table that mislabels a `diverged` destination, or a hand-over
block missing a flag, would pass every unit test.

**Closes when:** one run of the skill, from a fresh session, goes through all four steps in each mode —
*apply* on a machine with something missing, *hand over* on one where the printed commands are then
run as given — and the re-run report reads *N of N linked* both times.

### 5. The Copilot and project links are unproven on Windows

Opened 2026-09-13. `--agent copilot`, `--project` and `detect.py` were measured on macOS only.

| Unproven | Why it could differ |
|---|---|
| `--project` creates a junction per repo skill in `.claude\skills` | the macOS run made symlinks; the junction branch of `make_link` has only run for `~/.claude` |
| `--agent copilot` lands in `$HOME\.copilot\skills` and `copilot` loads it | the setup README marks Copilot CLI paths on Windows **not measured** |
| `detect.py` finds VS Code through `APPDATA` and probes `code` | on Windows `code` resolves to a `.cmd` shim, which the version probe runs directly |

**Closes when:** on the Windows machine, `python workstation\scripts\link_config.py --project --agent
copilot` reaches *N of N linked* after `--apply`, `/skills` in a `copilot` session lists the skills,
`python skills\setup-agents\scripts\detect.py` reports a VS Code version, and all three results are
recorded in `workstation/machines/windows-ema-pf5n4xe7.md`.

### 6. VS Code Copilot Chat has not been shown the workbench instructions

Opened 2026-09-13. `chat.useClaudeMdFile` is **not set** in this machine's VS Code user settings
(`detect.py`), so Chat does not read `~/.claude/CLAUDE.md` here. That the setting exists and defaults
to off is observed; that turning it on makes Chat load this repo's instructions through the link is
not.

**Closes when:** the user adds `"chat.useClaudeMdFile": true` to
`~/Library/Application Support/Code/User/settings.json`, a Chat session lists the instruction file in
its loaded context, `detect.py` reports `true`, and the machine note records it. The agent does not
make the edit — settings files are the user's.

### 7. Where `copilot plugin install` puts a plugin is unknown

Opened 2026-09-13, carried from the setup README's *How much of this was measured* table.

Not stated in the vendor page the CLI links, and no plugin is installed on either machine. It only
matters if skills are ever shipped to Copilot as a plugin instead of the `~/.copilot/skills` link that
now works — but until then the README's plugin commands describe an install nobody has watched.

**Closes when:** one plugin is installed with `copilot plugin install`, `copilot plugin list` shows it,
the directory it landed in is found and recorded in the setup README's table — or when the plugin
commands are removed from the README as a route this workbench does not use.

## Closed

Nothing yet. An item moves here with the evidence that closed it, or is deleted outright; a list of
things that turned out fine is not worth carrying.
