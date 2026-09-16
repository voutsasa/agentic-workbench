# Agentic Workbench

Enables engineers to set up their workstation and work in an agent-enabled environment: AI coding assistants configured consistently, on a toolchain that is known to work.

**Before you start**, the workstation needs two things this repo does not install:

- **Required — an AI coding assistant, installed and signed in.** The skills here are instructions an assistant carries out, so without one they do nothing. Claude Code and GitHub Copilot CLI both load them. `setup-agents` configures an assistant you already have; it does not install one.
- **Recommended — a package manager for the toolchain.** The install routes in [`workstation/cli/`](workstation/cli/README.md) assume Homebrew on macOS and Scoop on Windows, with `pipx` or `npm` for tools published to Python or Node registries. winget is noted where a tool offers it. A package manager keeps every tool installable and upgradable with one command, instead of by hand.

Start with the [`setup-agents`](skills/setup-agents/SKILL.md) skill — it finds the AI assistants on your machine and sets them up with the shared instructions and skills.

## Executive summary

The first two capabilities deliver the agent-enabled workstation; the last two keep it trustworthy.

| Capability | Role | What it gives engineers | Where |
|---|---|---|---|
| **Agent configuration** | Core | Every engineer's AI assistants follow the same instructions and skills, maintained in one place and applied to a machine in a guided step. | [`workstation/agent/`](workstation/agent/README.md) |
| **Workstation toolchain support for agents** | Core | The tools agents rely on come with proven install routes and known pitfalls, and each machine's real state is measured rather than assumed. | [`workstation/`](workstation/README.md) |
| **Rebuildable ingestion pipeline** | Integrity | The reference material behind that guidance is fetched from official sources on demand, so it can be refreshed instead of quietly ageing. | [`skills/ingest-source/`](skills/ingest-source/) |
| **Documentation validation gate** | Integrity | Before a change is shared, documented paths, commands and versions are checked against a real machine, so drift is caught before anyone relies on it. | [`workstation/agent/skills/verify-docs/`](workstation/agent/skills/verify-docs/SKILL.md) |

### Skills

Repo skills serve this workbench; global skills work in any repo. The authoritative lists are [`skills/README.md`](skills/README.md) and the `SKILLS` tuple in [`link_config.py`](workstation/scripts/link_config.py), and `workstation/scripts/tests/test_readme_skills.py`, run by the pre-push hook, refuses a push when this table stops matching them.

| Skill | Scope | What it does |
|---|---|---|
| [`setup-agents`](skills/setup-agents/SKILL.md) | repo | Sets up an engineer's AI coding assistants, confirming each choice, then applying shared instructions and skills or handing over commands. |
| [`ingest-source`](skills/ingest-source/SKILL.md) | repo | Adds a registered source to the knowledge base, filed under a predictable name and recorded in the catalogue for traceability. |
| [`fetch-to-markdown`](workstation/agent/skills/fetch-to-markdown/SKILL.md) | global | Converts web pages, PDFs or Office documents to clean markdown, routing each to the right tool and quality-checking the result. |
| [`verify-docs`](workstation/agent/skills/verify-docs/SKILL.md) | global | Audits documentation for stale claims by running a command that proves or refutes each, reporting them in an evidence table. |
| [`review`](workstation/agent/skills/review/SKILL.md) | global | Produces structured, read-only findings reports on documents or code, including regulatory texts and specs; applies fixes only when explicitly asked. |
| [`fix-findings`](workstation/agent/skills/fix-findings/SKILL.md) | global | Applies the most recent review's findings by following the review skill's Apply mode, escalating judgement calls instead of guessing them. |
| [`python-quality`](workstation/agent/skills/python-quality/SKILL.md) | global | Sets up code-quality checks for Python projects: linting, type checking, test coverage, complexity and dependency audits, calibrated to existing code. |
| [`pdf-deliverable`](workstation/agent/skills/pdf-deliverable/SKILL.md) | global | Turns markdown or HTML into PDFs, from working notes to formal documents meeting a required page layout or archival standard. |

## Layout

``` txt
SOURCES.md                	the register — source of truth.   
SOURCE_CATALOGUE.md       	one-line capability summary per source.   
TODO.md                   	open work carried between sessions.   
AGENTS.md                 	instructions for agents working in this repo.   
CLAUDE.md                 	imports AGENTS.md for Claude Code.   
.agents/rules/            	imports AGENTS.md for Antigravity.   

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
  machines/               	one file per machine — measured state, not policy.   
  scripts/                	the inventory probe and the ~/.claude link checker.   

scripts/                  	headless verify-docs runner.   
.github/workflows/        	weekly documentation audit — dormant on Azure DevOps.   

pyproject.toml            	Python project metadata.   
```

The top-level split is **`docs/` is what the workbench reads, `workstation/` is what it runs on, `skills/` is what it does.**

## The register and its process

| File | Role |
|---|---|
| [`SOURCES.md`](SOURCES.md) | **Source of truth.** The register of every source, grouped by the architecture layer it feeds, with the register conventions and per-layer gaps still to collect. Edit this first when adding or removing a source. |
| [`SOURCE_CATALOGUE.md`](SOURCE_CATALOGUE.md) | **Capability index.** One line per source saying what it gives you, mirroring the register's structure and entries exactly. Changes to the register need a matching change here. |
| [`skills/ingest-source/`](skills/ingest-source/) | **Process.** Where a register entry lands, what its file is called, what gets written back to the catalogue, and how workstation tooling additionally gets its install route or registration recorded. A skill rather than a guide, so it is discovered by what you are doing rather than by knowing its filename. |
| [`workstation/agent/skills/fetch-to-markdown/`](workstation/agent/skills/fetch-to-markdown/) | **Conversion.** How to route a document into clean markdown — GitHub repo, PDF, plain doc site, or JS-hydrated site — and how to quality-check the result. Register-free and **global**: linked into `~/.claude/skills/`, so it works on any document in any repo. |
| [`TODO.md`](TODO.md) | **Open work.** Committed new work and unproven existing gaps, each item with the evidence that would close it. |
| [`workstation/cli/README.md`](workstation/cli/README.md) | **CLI tool index.** What each per-tool file is for, a `command → product → folder` map, and the version-currency rule. |
| [`workstation/mcp/README.md`](workstation/mcp/README.md) | **MCP server index.** The third-party servers configured into this machine, and the file contract they follow. |
| [`workstation/machines/README.md`](workstation/machines/README.md) | **Machine index.** One file per machine this workbench runs on, and the test for whether a fact is policy, a route, or machine state. |
| [`AGENTS.md`](AGENTS.md) | **Agent instructions for this repo** — file roles, the layer model, the ingestion invariant, and the rule that GitHub sources are fetched as raw READMEs rather than cloned. Read directly by GitHub Copilot; Claude Code reaches it through [`CLAUDE.md`](CLAUDE.md) and Antigravity through [`.agents/rules/workbench.md`](.agents/rules/workbench.md), each a one-line `@AGENTS.md` import. |
## The workstation — `workstation/`

What the workbench runs on — the machines, not an architecture.

**[`workstation/README.md`](workstation/README.md) is the map** — what each subfolder holds, where to start in it, and the rules spanning all of them. The summary:

| Path | Role |
|---|---|
| [`workstation/cli/`](workstation/cli/README.md) | The CLI toolchain. One folder per tool: authored `install.md` and `quick_start.md`, plus an ingested `reference.md`. Read `quick_start.md` before invoking a tool you haven't used this session. |
| [`workstation/mcp/`](workstation/mcp/README.md) | Third-party MCP servers. One folder per server: authored `setup.md` plus an ingested `reference.md`. |
| [`workstation/machines/`](workstation/machines/README.md) | One file per machine: paths, shell, which tools actually run, what is broken. **The only place a machine-specific fact belongs.** |
| [`workstation/scripts/`](workstation/scripts/README.md) | Scripts maintaining this tree. `inventory.py` probes the toolchain and generates a machine's tool table; `link_config.py` reports or repairs the `~/.claude` links, and with `--agent copilot` the `~/.copilot/skills` links. Both are read-only unless told otherwise. |
| `workstation/agent/` | Claude Code configuration, **linked into `~/.claude/`** so it is versioned rather than scattered across a home directory. See below. |

**The split is by lifetime, not by platform** — policy, route and machine state live in different
files. [`workstation/machines/README.md`](workstation/machines/README.md) has the table and the test.

### `workstation/agent/`

Edits to `~/.claude/CLAUDE.md` or the `review` skill land here, because those paths are links into this directory.

**Everything here is shared by every machine, unmodified.** Anything machine-specific goes in `workstation/machines/`; anything machine-*local* and not compliance-bound goes in `~/.claude/settings.local.json`, which is untracked by design.

| Path | Role |
|---|---|
| `workstation/agent/README.md` | The contract: what is linked where, and what is deliberately left untracked. |
| `workstation/agent/setup/<platform>.md` | Per-platform setup for a new machine. macOS uses symlinks; Windows uses junctions and hardlinks, because symlinks there need admin. |
| `workstation/agent/AGENT-INSTRUCTIONS.md` | Global instructions applying to every project — linked to `~/.claude/CLAUDE.md`. Policy only, no platform, no paths. |
| `workstation/agent/settings.json` | Reference copy of the shared Claude Code settings — **merged into `~/.claude/settings.json` by hand, never linked.** [Why, and the procedure](workstation/agent/README.md#settings-are-merged-never-linked). |
| `workstation/agent/skills/<skill>/` | The skills promoted to global scope, each linked to `~/.claude/skills/<skill>`. Which skills those are is [`link_config.py`](workstation/scripts/link_config.py)'s `SKILLS` tuple — see [`skills/README.md`](skills/README.md). A skill earns promotion here by working in a repo that is not this one; until then it stays in [`skills/`](skills/). `SKILL.md` is a skill's definition; `scripts/` and `tests/` hold its repeatable actions. |

Because these are links into a git repo, check `git status` here before overwriting or regenerating any of them — and if this directory is ever moved or renamed, **repoint the links**, or every session silently loses its global instructions. On Windows `CLAUDE.md` and `machine.md` are hardlinks and any atomic-saving editor severs them silently; [`workstation/agent/setup/windows.md`](workstation/agent/setup/windows.md) carries the detection command.

## Repo mechanics

| Path | Role |
|---|---|
| [`skills/README.md`](skills/README.md) | Index of this repo's own skills, the line dividing them from the global ones in `workstation/agent/skills/`, and the per-clone symlink that makes them load — Claude Code discovers `.claude/skills/`, not `skills/`. |
| `pyproject.toml` | Project metadata. No runtime dependencies; the `dev` dependency group supplies `pytest` and `ruff` for repository quality checks. |
| `.python-version` | Pins the interpreter for `uv` — currently 3.14. |
| `.verify-claims-allow` | Path claims the documentation gate is to leave alone, one glob per line with a reason above each. Repo-local on purpose: the pre-push hook is shared by every repo that links it, so exemptions must not travel with it. |
| `.pre-push-tests` | Unit-test directories the pre-push hook runs before a push, one per line. Repo-local for the same reason. |
| `.gitignore` | Excludes the ingested corpus, `.venv/`, `.DS_Store`, and Python build artefacts. |
| `.github/workflows/verify-docs.yml` | Weekly documentation audit on GitHub Actions, opening a pull request with the reports. **Dormant:** the repo is hosted on Azure DevOps, where it does not run — porting it is [`TODO.md`](TODO.md) #9. |
| `scripts/verify-docs.sh` | Headless `verify-docs` run through `claude -p`, writing a report and editing no documentation. Called by the dormant workflow above; runnable by hand with `ANTHROPIC_API_KEY` set. |

## What is tracked in git

Everything authored is tracked; the ingested third-party corpus is not, so a fresh clone's corpus is empty by design. [`AGENTS.md` § *The corpus is not in git*](AGENTS.md#the-corpus-is-not-in-git) has what is excluded and when to rebuild.
