# Agentic Workbench

Gathers agentic-engineering source material used to build constitutions, skills, and other artefacts for projects adopting Spec-Driven Development.

Start with [`SOURCE_CATALOGUE.md`](SOURCE_CATALOGUE.md) — it lists every source with a one-line summary of what it gives you, grouped by architecture layer.

## Executive summary

### Key technical capabilities

| Capability | What it provides | Where |
|---|---|---|
| **Layered source register** | Every source grouped by the architecture layer it feeds — business domain, solution, data, technical, implementation — with a one-line capability summary each. | [`SOURCES.md`](SOURCES.md), [`SOURCE_CATALOGUE.md`](SOURCE_CATALOGUE.md) |
| **Rebuildable ingestion pipeline** | One register entry becomes one clean markdown file, routed to the right CLI tool (curl, pandoc, docling, Playwright + defuddle) and quality-checked. The corpus is gitignored and rebuilt from the register. | [`skills/ingest-source/`](skills/ingest-source/) |
| **Workstation toolchain guidance** | Per-tool install routes and run-time traps for the CLI tools and MCP servers, plus per-machine state measured by `inventory.py` rather than written by hand. | [`workstation/`](workstation/README.md) |
| **Agent configuration as code** | Global agent instructions and skills versioned here and linked into `~/.claude/` and `~/.copilot/skills/` by `link_config.py`; `settings.json` is merged by hand, never overwritten. | [`workstation/agent/`](workstation/agent/README.md) |
| **Documentation gates** | A pre-push hook runs `repo_check.py` for internal consistency and `verify_claims.py`, which executes each documented path, flag and version claim against the real machine. | [`workstation/agent/skills/review/scripts/`](workstation/agent/skills/review/scripts/README.md) |

### Skills

Repo-local skills name this workbench's register and folders; global skills work in any repo. The authoritative lists are [`skills/README.md`](skills/README.md) and the `SKILLS` tuple in [`link_config.py`](workstation/scripts/link_config.py).

| Skill | Scope | What it does |
|---|---|---|
| [`ingest-source`](skills/ingest-source/SKILL.md) | repo | Pulls one registered source into the corpus: resolves its destination and filename, delegates conversion, then records it in the catalogue. |
| [`setup-agents`](skills/setup-agents/SKILL.md) | repo | Detects the machine's AI assistants, asks which to configure and Claude's provider, links workbench instructions and skills or supplies commands. |
| [`fetch-to-markdown`](workstation/agent/skills/fetch-to-markdown/SKILL.md) | global | Converts web pages, PDFs or Office documents to clean markdown, routing each to the right tool and quality-checking the result. |
| [`review`](workstation/agent/skills/review/SKILL.md) | global | Produces structured, read-only findings reports on documents or code, including regulatory texts and specs; applies fixes only when explicitly asked. |
| [`fix-findings`](workstation/agent/skills/fix-findings/SKILL.md) | global | Applies the most recent review's findings by following the review skill's Apply mode, escalating judgement calls instead of guessing them. |
| [`verify-docs`](workstation/agent/skills/verify-docs/SKILL.md) | global | Audits documentation for stale claims by running a command that proves or refutes each, reporting them in an evidence table. |
| [`python-quality`](workstation/agent/skills/python-quality/SKILL.md) | global | Sets up Python quality gates: ruff, pyright, pytest coverage, radon, dependency audit and docs, with thresholds derived from existing code. |
| [`pdf-deliverable`](workstation/agent/skills/pdf-deliverable/SKILL.md) | global | Produces PDFs from markdown or HTML without LaTeX: pandoc via typst for working notes, WeasyPrint for a specified page format. |

## Layout

``` txt
SOURCES.md                	the register — source of truth.   
SOURCE_CATALOGUE.md       	one-line capability summary per source.   
TODO.md                   	open work carried between sessions.   
CLAUDE.md                 	instructions for agents working in this repo.   

docs/                     	the corpus — what the workbench reads.   
  landing-zone/           	ingested external sources     — not in git.   
  guidance/               	distilled agent-facing notes  — in git.   

skills/                   	this repo's own skills — what the workbench does.   
  README.md               	the repo-local vs. global line, and how to load these.   
  ingest-source/          	turns one register entry into a corpus file.   
  setup-agents/           	detects the machine's AI assistants and links the config for them.   

workstation/              	this machine's setup — serves the repo, never a deliverable.   
  README.md               	what each subfolder below is for.   
  cli/README.md           	the CLI toolchain index.   
  cli/<tool>/             	per-tool CLI guidance         — authored files in git.   
  mcp/README.md           	the MCP server index.   
  mcp/<server>/           	per-server MCP guidance       — authored files in git.   
  agent/                  	agent config + global skills, symlinked into ~/.claude/.   

pyproject.toml            	Python project metadata.   
```

The top-level split is **`docs/` is what the workbench reads, `workstation/` is what it runs on, `skills/` is what it does.** Nothing under `workstation/` should ever reach a generated artefact — it describes the machines this runs on, not an architecture.

## The register and its process

| File | Role |
|---|---|
| [`SOURCES.md`](SOURCES.md) | **Source of truth.** The register of every source, grouped by the architecture layer it feeds, with the register conventions and per-layer gaps still to collect. Edit this first when adding or removing a source. |
| [`SOURCE_CATALOGUE.md`](SOURCE_CATALOGUE.md) | **Capability index.** One line per source saying what it gives you, mirroring the register's structure and entries exactly. Changes to the register need a matching change here. |
| [`skills/ingest-source/`](skills/ingest-source/) | **Process.** Where a register entry lands, what its file is called, what gets written back to the catalogue, and how workstation tooling additionally gets its install route or registration recorded. A skill rather than a guide, so it is discovered by what you are doing rather than by knowing its filename. |
| [`workstation/agent/skills/fetch-to-markdown/`](workstation/agent/skills/fetch-to-markdown/) | **Conversion.** How to route a document into clean markdown — GitHub repo, PDF, plain doc site, or JS-hydrated site — and how to quality-check the result. Register-free and **global**: linked into `~/.claude/skills/`, so it works on any document in any repo. |
| [`TODO.md`](TODO.md) | **Open work.** What is unproven rather than unwritten, each item with the evidence that would close it. |
| [`workstation/cli/README.md`](workstation/cli/README.md) | **CLI tool index.** What each per-tool file is for, a `command → product → folder` map, and the version-currency rule. |
| [`workstation/mcp/README.md`](workstation/mcp/README.md) | **MCP server index.** The third-party servers configured into this machine, and the file contract they follow. |
| [`workstation/machines/README.md`](workstation/machines/README.md) | **Machine index.** One file per machine this workbench runs on, and the test for whether a fact is policy, a route, or machine state. |
| [`CLAUDE.md`](CLAUDE.md) | **Agent instructions for this repo** — file roles, the layer model, the ingestion invariant, and the rule that GitHub sources are fetched as raw READMEs rather than cloned. Read by Claude Code automatically. |
## The workstation — `workstation/`

What the workbench runs on. This tree describes **the machines it runs on**, not an architecture, so nothing in it should reach a generated artefact.

**[`workstation/README.md`](workstation/README.md) is the map** — what each subfolder holds, where to start in it, and the rules spanning all of them. The summary:

| Path | Role |
|---|---|
| [`workstation/cli/`](workstation/cli/README.md) | The CLI toolchain. One folder per tool: authored `install.md` and `quick_start.md`, plus an ingested `reference.md`. Read `quick_start.md` before invoking a tool you haven't used this session. |
| [`workstation/mcp/`](workstation/mcp/README.md) | Third-party MCP servers. One folder per server: authored `setup.md` plus an ingested `reference.md`. |
| [`workstation/machines/`](workstation/machines/README.md) | One file per machine: paths, shell, which tools actually run, what is broken. **The only place a machine-specific fact belongs.** |
| [`workstation/scripts/`](workstation/scripts/README.md) | Scripts maintaining this tree. `inventory.py` probes the toolchain and generates a machine's tool table; `link_config.py` reports or repairs the `~/.claude` links, and with `--agent copilot` the `~/.copilot/skills` links. Both are read-only unless told otherwise. |
| `workstation/agent/` | Claude Code configuration, **linked into `~/.claude/`** so it is versioned rather than scattered across a home directory. See below. |

**The split is by lifetime, not by platform.** Policy never expires, a route expires slowly, machine
state expires constantly — so they live in three different files rather than one. This is why
`install.md` carries no current version and `CLAUDE.md` names no platform.
[`workstation/machines/README.md`](workstation/machines/README.md) has the test for which file a given
fact belongs in.

### `workstation/agent/`

Edits to `~/.claude/CLAUDE.md` or the `review` skill land here, because those paths are links into this directory.

**Everything here is shared by every machine, unmodified.** Anything machine-specific goes in `workstation/machines/`; anything machine-*local* and not compliance-bound goes in `~/.claude/settings.local.json`, which is untracked by design.

**`settings.json` is the one file that is merged rather than linked.** Claude Code writes to the live `~/.claude/settings.json` itself, and on a provider-bound machine it also carries an `env` block this repo deliberately does not hold — so nothing here may overwrite the live copy. Which machines are provider-bound is recorded in `workstation/machines/`. [`workstation/agent/README.md`](workstation/agent/README.md#settings-are-merged-never-linked) has the procedure.

| Path | Role |
|---|---|
| `workstation/agent/README.md` | The contract: what is linked where, and what is deliberately left untracked. |
| `workstation/agent/setup/<platform>.md` | Per-platform setup for a new machine. macOS uses symlinks; Windows uses junctions and hardlinks, because symlinks there need admin. |
| `workstation/agent/AGENT-INSTRUCTIONS.md` | Global instructions applying to every project — linked to `~/.claude/CLAUDE.md`. Policy only, no platform, no paths. |
| `workstation/agent/settings.json` | Reference copy of the shared Claude Code settings — **merged into `~/.claude/settings.json` by hand, never linked.** Carries no `env` block on purpose. |
| `workstation/agent/skills/<skill>/` | The skills promoted to global scope, each linked to `~/.claude/skills/<skill>`. [`link_config.py`](workstation/scripts/link_config.py)'s `SKILLS` tuple is the authoritative list of which skills those are; prose that repeats it goes stale, which is why no copy of it appears here. A skill earns promotion here by working in a repo that is not this one; until then it stays in [`skills/`](skills/). `SKILL.md` is a skill's definition; `scripts/` and `tests/` hold its repeatable actions. |

Because these are links into a git repo, check `git status` here before overwriting or regenerating any of them — and if this directory is ever moved or renamed, **repoint the links**, or every session silently loses its global instructions. On Windows `CLAUDE.md` and `machine.md` are hardlinks and any atomic-saving editor severs them silently; [`workstation/agent/setup/windows.md`](workstation/agent/setup/windows.md) carries the detection command.

## Repo mechanics

| Path | Role |
|---|---|
| [`skills/README.md`](skills/README.md) | Index of this repo's own skills, the line dividing them from the global ones in `workstation/agent/skills/`, and the per-clone symlink that makes them load — Claude Code discovers `.claude/skills/`, not `skills/`. |
| `pyproject.toml` | Project metadata. No dependencies: the workbench runs on the workstation CLI toolchain plus the standard library. |
| `.python-version` | Pins the interpreter for `uv` — currently 3.14. |
| `.verify-claims-allow` | Path claims the documentation gate is to leave alone, one glob per line with a reason above each. Repo-local on purpose: the pre-push hook is shared by every repo that links it, so exemptions must not travel with it. |
| `.gitignore` | Excludes the ingested corpus, `.venv/`, `.DS_Store`, and Python build artefacts. |

## What is tracked in git

The register, the guides, the authored guidance notes in `docs/guidance/`, the authored CLI and MCP guidance, and the agent config. **Not** the ingested third-party content — `docs/landing-zone/`, `workstation/cli/*/reference.md`, and `workstation/mcp/*/reference.md` are all excluded.

On a fresh clone the corpus is therefore empty and every register entry will look un-ingested. That is expected. Rebuilding it is a deliberate, potentially long operation — see [`skills/ingest-source/`](skills/ingest-source/).
