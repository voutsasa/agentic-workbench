# Agentic-workbench

Enables engineers to set up their workstation and work in an agent-enabled environment: AI coding assistants configured consistently, on a toolchain that is known to work.

## File roles

| Path | Role |
|---|---|
| `AGENTS.md` | **This file** — the repo's agent instructions, and the only copy. Read directly by GitHub Copilot; every other assistant reaches it through a one-line import, never a second copy. |
| `CLAUDE.md` | One line, `@AGENTS.md`. Claude Code reads `CLAUDE.md` and not `AGENTS.md`, so this is its route in. Add nothing else here. |
| `.agents/rules/workbench.md` | One line, `@AGENTS.md` — Google Antigravity's route in, as a workspace rule. Its activation (**Always On**) is set in Antigravity's UI. |
| `SOURCES.md` | The source register created by the user. **Source of truth** for what belongs in the project. Sources are grouped by the architecture layer each feeds. Edit this first when adding or removing a source. This document should not be used as a reference to any other document. Where required refer to `SOURCE_CATALOGUE.md` |
| `SOURCE_CATALOGUE.md` | One-sentence (≤20 words) capability summary per source, mirroring `SOURCES.md`'s structure and entries exactly. Whenever `SOURCES.md` changes, `SOURCE_CATALOGUE.md` needs a matching update. |
| `README.md` | The repo's landing page: what the workbench is, plus the role of every file in it. Carries no source entries — those live in `SOURCE_CATALOGUE.md`. |
| `TODO.md` | Open work carried between sessions, each item saying what would close it. Two kinds of item: **new work** that has been committed to, and **existing gaps** — something written that no run has proven — never an idea nobody has committed to. An item is deleted when its evidence exists, not when it feels handled. |
| `skills/<skill>/` | **This repo's own skills** — procedures that name `SOURCES.md`, `docs/landing-zone/` or `workstation/`, so they are wrong anywhere else. The counterpart to `workstation/agent/skills/`, which is global. `skills/README.md` carries the line between the two and the per-clone symlink that makes these load, since Claude Code discovers `.claude/skills/` and not this folder. |
| `skills/ingest-source/` | Pulls one `SOURCES.md` entry into the corpus: resolve where it lands and what it is named, delegate the conversion to `fetch-to-markdown`, record it in `SOURCE_CATALOGUE.md`. `references/workstation-tooling.md` is the branch for CLI tools and MCP servers. Register mechanics only — no routing, no conversion. |
| `skills/setup-agents/` | Identifies the machine and the AI assistants on it (`skills/setup-agents/scripts/detect.py`, read-only), asks which to set up, which provider Claude uses and whether the workbench config goes global, describes every change, then either applies the links through `link_config.py` or hands the user the commands. Orchestrates `workstation/agent/setup/` — carries no route of its own and never writes a settings file. |
| `docs/landing-zone/` | Ingested external sources — flat, machine-written, **not hand-edited** and **not in git** (see below). |
| `docs/guidance/` | Short, agent-facing notes to apply mid-task, plus the assets their commands depend on. Hand-authored, tracked in git. Every note declares its provenance; `docs/guidance/README.md` sets the bar and is the file to read before adding one. |
| `workstation/README.md` | Map of the `workstation/` tree — what each subfolder is for and where to start in it. |
| `workstation/cli/README.md` | Index of the workstation **CLI tools** only: what each per-tool file is for, a `command → product → folder` map, and the version-currency rule. Its MCP counterpart is `workstation/mcp/README.md`. |
| `workstation/cli/<tool>/` | Per-tool guidance for the workstation CLI tools. `install.md` and `quick_start.md` are hand-authored, short, and tracked; `reference.md` is that tool's ingested page — machine-written and **not in git**. Read `quick_start.md` before invoking a tool you haven't used this session. |
| `workstation/mcp/README.md` | Index of the third-party **MCP servers** configured into this machine. The sibling of `workstation/cli/README.md`, and where the two-file contract is explained. |
| `workstation/mcp/<server>/` | Per-server guidance. Authored `setup.md` (tracked) plus the ingested `reference.md` (**not in git**). Servers *authored* here are project output and do not belong in this tree. |
| `workstation/agent/` | Claude Code configuration, **linked into `~/.claude/`** — `AGENT-INSTRUCTIONS.md` (linked as `~/.claude/CLAUDE.md`) and the global skills. Which skills those are is `link_config.py`'s `SKILLS` tuple — never a prose copy (`skills/README.md`). **Shared by every machine, unmodified: nothing machine-specific may be added here.** Editing any of those paths writes here, so check `git status` first. If this directory is moved or renamed, the links must be repointed or every session silently loses its global instructions. `settings.json` is the exception — see the row below. |
| `workstation/agent/skills/fetch-to-markdown/` | **Global, not workbench-specific.** One URL and one caller-given destination path to clean markdown: classify the page, route it (raw README, curl, extractor plus pandoc, docling, Playwright plus defuddle), quality-check, strip base64 images. `scripts/` holds the two stdlib-only converters, `tests/` their `unittest` suite. Promoted out of `skills/ingest-source/` because it names no register and no destination directory — do not add one. |
| `workstation/agent/settings.json` | Reference copy of the shared Claude Code settings, **merged into `~/.claude/settings.json` by hand — never linked, and never overwritten by any command.** Why, and the merge procedure: `workstation/agent/README.md` § *Settings are merged, never linked*. |
| `workstation/agent/setup/<platform>.md` | Per-platform route for putting that config in place on a new machine — symlinks on macOS, junctions plus hardlinks on Windows. Read the *Before you start* section: both routes overwrite `~/.claude/CLAUDE.md`, and neither touches `settings.json`. |
| `workstation/machines/<platform>-<id>.md` | **Per-machine state** — repo path, shell, which CLI tools actually run, which skills are installed, what is blocked. The only place a machine-specific fact belongs, and where `CLAUDE.md` and `install.md` deliberately do not carry one. Its tool table is generated by `workstation/scripts/inventory.py`, not hand-written. `workstation/machines/README.md` is the index and carries the test for classifying a fact. |
| `workstation/scripts/` | Scripts maintaining the `workstation/` tree — stdlib-only so they run on a fresh clone. `inventory.py` probes the toolchain; `link_config.py` reports or repairs the `~/.claude` links — and, with `--agent copilot`, the `~/.copilot/skills` links — and never touches `settings.json`. Both write nothing by default. Tests in `workstation/scripts/tests/` use `unittest`. |
| `.verify-claims-allow` | Globs the pre-push documentation gate exempts from path checking — paths that are *meant* not to exist here, such as files a skill writes into a target project. One glob per line, each with a reason above it. Repo-local by design: the hook is shared across repos, so an exemption written into it would leak. A path that should exist and does not is a defect to fix, never an entry here. |
| `.pre-push-tests` | Unit-test directories the pre-push hook runs, one per line. Repo-local for the same reason as `.verify-claims-allow`. It names `workstation/scripts/tests`, which holds `README.md`'s skill table to the real skills, and every skill's `tests/` folder. |
| `.github/workflows/verify-docs.yml` | Weekly documentation audit on GitHub Actions: `verify_claims.py --online`, then `scripts/verify-docs.sh`, then a pull request carrying both reports. **Dormant** — the repo is hosted on Azure DevOps, where GitHub workflows do not run. Porting it is `TODO.md` #9. |
| `scripts/verify-docs.sh` | Headless run of the `verify-docs` skill through `claude -p`. Writes a report and edits no documentation; needs `ANTHROPIC_API_KEY`. Its only automated caller is the dormant workflow above. |

**Top-level split:** `docs/` is what the workbench reads; `workstation/` is what it runs on; `skills/` is what it does. Nothing under `workstation/` should reach a generated artefact — it describes the machines this runs on, not an architecture.

**Inside `workstation/`, the split is by lifetime:** policy, route and machine state live in different files. Before adding a fact there, apply the test in `workstation/machines/README.md` — *would this still be true on the other machine?*

## The layer model

Sources are grouped by the architecture layer they feed, not by technology: business domain, solution architecture, data architecture, technical architecture, and implementation architecture. The first four are **inputs**; implementation architecture is the **per-project output** the workbench exists to produce.

Two cross-cutting groups sit outside the layer model deliberately — *agent working practice* governs how the agent works rather than how the system is built, and *workstation tooling* serves this repo only. Neither should leak into a generated artefact as though it were architecture.

`SOURCES.md` holds the full layer definitions, the register conventions, and the per-layer gaps still to be collected.

## The corpus is not in git

`.gitignore` excludes `docs/landing-zone/`, `workstation/cli/*/reference.md`, and `workstation/mcp/*/reference.md`. The repo tracks the register, the guides, the authored notes in `docs/guidance/`, the authored `install.md`/`quick_start.md` pairs, and the authored `setup.md` files — **not** the ingested third-party content, which is rebuildable from `SOURCES.md`.

On a fresh clone the corpus is therefore empty and every entry will look un-ingested. That is expected, not a fault. Rebuilding it is a deliberate, potentially long operation: only do a full ingestion run when explicitly asked. Otherwise assume a populated local corpus and ingest only the delta for entries whose files are genuinely missing.

## Ingestion invariant

Every `[bracket link]` entry in `SOURCES.md` should have a corresponding file at `docs/landing-zone/<bracket text>.{md,pdf}`, writing a `: ` in the title — the colon *and* the space after it — as ` - ` in the filename. If a file is missing or an entry was just added, that source hasn't been ingested yet — run it through the `ingest-source` skill (only the missing delta, not a full re-run).

**One destination exception, two trees.** Entries under *Cross-cutting aspects → 2. Workstation tooling* land beside their authored guidance instead of in `docs/landing-zone/` — under `#### CLI tools` at `workstation/cli/<bracket text>/reference.md`, and under `#### MCP servers` at `workstation/mcp/<bracket text>/reference.md`. The invariant is otherwise unchanged: still one bracket link to one ingested file, still named from the bracket text.

One exclusion: italic *see also* cross-references are not entries. Every real entry carries exactly one bracket link with an `http(s)` target, so the check stays one-to-one.

## The user installs; the agent records

Workstation tooling — CLI tools and MCP servers alike — is installed, registered, and upgraded **by the user, never by the agent**. Resolving the route, checking the package is genuine, and writing it into `install.md` or `setup.md` is the agent's work. Running `brew install`, `claude mcp add`, or an upgrade is not: it changes the user's machine, and a tool that shifts version mid-task breaks the work in progress.

Hand over the exact command and let them run it. An entry in the register means a route has been recorded, **not** that the tool is live here — verify before assuming it runs, and mark anything you could not observe as pending rather than guessing at it.

## Hard rule

For any `github.com/<owner>/<repo>` source URL, fetch the raw README directly (e.g. `raw.githubusercontent.com/<owner>/<repo>/<branch>/README.md`). Never `git clone` the repo — only the README is needed.
