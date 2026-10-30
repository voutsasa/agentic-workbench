# Agentic Workbench

Enables engineers to set up their workstation and work in an agent-enabled environment: AI coding assistants configured consistently, on a toolchain that is known to work.

**Before you start**, the workstation needs two things this repo does not install:

- **Required — Git, Python3, `uv`, Node.js/npm, and an AI coding assistant, externally provisioned.** The skills here are instructions an assistant carries out, so without one they do nothing. Claude Code and GitHub Copilot CLI both load them. `get-workstation-status` reports their presence and versions; it does not install or authenticate them. Git gets the clone; Python runs the workstation scripts; `uv` creates every project venv, which the global instructions require for any Python beyond those bootstrap scripts; Node.js/npm supplies the Node-based toolchain components.
- **Recommended — a package manager for the toolchain.** The install routes in [`workstation/cli/`](workstation/cli/README.md) assume Homebrew on macOS and Scoop on Windows, with `uv tool` (pipx only where a tool's `install.md` records why uv cannot work) or `npm` for tools published to Python or Node registries. winget is noted where a tool offers it. A package manager keeps every tool installable and upgradable with one command, instead of by hand.

## Install

A fresh clone loads nothing on its own: the venv, the pre-push hook, the repo skills and Claude Code's `CLAUDE.md` are all per-clone and gitignored. Run these from the repo root before the first session. Use `python3` on macOS and `python` on Windows; the scripts are stdlib-only, so they run before a venv exists.

**1. Create the venv and install the development tools.** `uv sync` creates `.venv` on the Python pinned by `.python-version` (fetching it if missing) and installs the `dev` group — `pytest`, `ruff`, `pyright`, `git-cliff` — from `uv.lock`. The pre-push hook runs ruff, Pyright through the venv interpreter, and the test suites on this venv.

```sh
uv sync
```

**2. Install the pre-push gate.** It is per-clone, so a fresh clone pushes unchecked until it is in place.

| Platform | Run |
|---|---|
| macOS | `ln -sfn ../../workstation/agent/skills/review/scripts/pre-push .git/hooks/pre-push` |
| Windows | copy the shim, as in [`workstation/agent/setup/windows.md` § *The pre-push gate*](workstation/agent/setup/windows.md#the-pre-push-gate) |

**3. Check the workstation.** The report lists every prerequisite and CLI tool with its status, version and the command that fixes it, and names the skills each tool serves. It installs nothing and exits non-zero only when a required prerequisite fails. On a machine with no note in `workstation/machines/` yet, first follow [*Adding a machine*](workstation/machines/README.md#adding-a-machine).

```sh
python workstation/scripts/status.py
```

**4. Set up Claude Code and/or GitHub Copilot CLI.** Two routes, not mutually exclusive — the full
route for working *in* this repo, the plugin for just picking up its global skills elsewhere.

**Full route — everything this repo gives an assistant**: this repo's own skills
(`get-workstation-status`, `ingest-source`, `setup-agents`), the shared instructions, and the global
skills, all linked per clone:

| You use | Run | It puts in place |
|---|---|---|
| Claude Code, alone or with Copilot | `python workstation/scripts/link_config.py --project --claude-md --apply` | `.claude/skills/` links, and `CLAUDE.md` holding `@AGENTS.md` |
| GitHub Copilot only | `python workstation/scripts/link_config.py --project --apply` | `.claude/skills/` links. No `CLAUDE.md`: Copilot reads `AGENTS.md` directly, and reads `CLAUDE.md` too, so adding it would load the instructions twice |

Then start the assistant in the repo — restart it if a session was already open, since instructions are read at session start — and run the [`setup-agents`](skills/setup-agents/SKILL.md) skill. It finds the AI assistants on your machine and sets them up with the shared instructions and skills. Re-run either command without `--apply` to check: it exits non-zero unless everything reads `linked`.

**Plugin route — just the global skills**, one OS-independent command per tool, no Python step, no
symlink-vs-junction branch. Use the **absolute path** to your clone — both tools resolve it again on
every later command, so a relative path only works for as long as you happen to run from the repo
root. Replace `<agentic-workbench>` with where you cloned this repo (e.g.
`/Users/<you>/Development/agentic-coding/agentic-workbench` on macOS,
`C:\Users\<you>\...\agentic-workbench` on Windows):

```sh
# Claude Code
claude plugin marketplace add <agentic-workbench>/workstation/agent
claude plugin install workbench-skills@agentic-workbench

# Copilot CLI
copilot plugin marketplace add <agentic-workbench>/workstation/agent
copilot plugin install workbench-skills@agentic-workbench
```

This gets you `review`, `verify-docs`, `fetch-to-markdown`, `python-quality`, `pdf-deliverable`,
`fix-findings`, `confluence-publish`, `confluence-export`, `setup-mcp-servers` and `session-signature` — not this repo's
own `SOURCES.md`/register-aware skills, and not the shared instructions, since both assume the full
clone. [`workstation/agent/README.md` § *Install the skills as a plugin
instead*](workstation/agent/README.md#install-the-skills-as-a-plugin-instead) has the manifest layout
and the verify step.

**5. Optional — observe sessions in Langfuse.** Only Claude Code has a Langfuse marketplace plugin;
GitHub Copilot CLI has no Langfuse plugin and is wired instead through its own built-in
OpenTelemetry export, pointed at Langfuse's OTLP endpoint; Kiro has neither, and is wired through a
pair of hook files copied into the project. All three need a Langfuse project and its public/secret
API keys first.

*Claude Code — plugin:*

```sh
claude plugin marketplace add langfuse/Claude-Observability-Plugin
claude plugin install langfuse-observability@langfuse-observability
```

Restart Claude Code, then set the keys from inside a session (the secret key is held in the OS
keychain, not a file):

```text
/plugin configure langfuse-observability@langfuse-observability
```

Switch it on/off without uninstalling:

```sh
claude plugin enable langfuse-observability@langfuse-observability
claude plugin disable langfuse-observability@langfuse-observability
```

Needs `uv` on `PATH` (falls back to `python3` 3.10+ with `langfuse>=4.7,<5`). Troubleshooting log:
`~/.claude/state/langfuse_hook.log`; set `CC_LANGFUSE_DEBUG` for verbose output.

*GitHub Copilot CLI — OTEL export, no install step:*

```sh
export COPILOT_OTEL_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT="https://cloud.langfuse.com/api/public/otel"
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic <base64 of pk-lf-...:sk-lf-...>,x-langfuse-ingestion-version=4"
export OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true
```

Switch off with `export COPILOT_OTEL_ENABLED=false` (or unset the variable). Put the exports in your
shell profile to persist them; a shell restart (or re-sourcing the profile) is what turns tracking on
or off, since the CLI reads these at startup.

*Kiro — project hooks, no plugin:*

```sh
git clone https://github.com/langfuse/langfuse-examples.git
cp -r langfuse-examples/applications/kiro-langfuse/.kiro/hooks/ your-project/.kiro/hooks/
cp -r langfuse-examples/applications/kiro-langfuse/hooks/ your-project/hooks/
cd your-project/hooks && npm install
```

Then put `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` (and, outside the EU, `LANGFUSE_BASE_URL`)
in a `.env` file at the project root. Switch tracking on/off per hook, not globally: open the Hook UI
(`Cmd/Ctrl+Shift+P` → "Kiro: Open Kiro Hook UI") and toggle each of the 10 hooks under
`.kiro/hooks/`, or edit `"enabled": true`/`false` directly in each hook's `.kiro.hook` file.

## Executive summary

The first two capabilities deliver the agent-enabled workstation; the last two keep it trustworthy.

| Capability | Role | What it gives engineers | Where |
|---|---|---|---|
| **Agent configuration** | Core | Every engineer's AI assistants follow the same instructions and skills, maintained in one place and applied to a machine in a guided step. | [`workstation/agent/`](workstation/agent/README.md) |
| **Workstation toolchain support for agents** | Core | The tools agents rely on come with proven install routes and known pitfalls, and each machine's real state is measured rather than assumed. | [`workstation/`](workstation/README.md) |
| **Rebuildable ingestion pipeline** | Integrity | The reference material behind that guidance is fetched from official sources on demand, so it can be refreshed instead of quietly ageing. | [`skills/ingest-source/`](skills/ingest-source/) |
| **Documentation validation gate** | Integrity | Before a change is shared, documented paths, commands and versions are checked against a real machine, so drift is caught before anyone relies on it. | [`workstation/agent/skills/verify-docs/`](workstation/agent/skills/verify-docs/SKILL.md) |
| **Agentic development plan** | Education | Development plan for software architects/developers, data scientists, devops engineers or other roles involved in the SDLC. | [Agentic development plan](docs/guidance/DEVELOPMENT-PLAN.md) |

### Skills

Repo skills serve this workbench; global skills work in any repo. The authoritative lists are [`skills/README.md`](skills/README.md) and the `SKILLS` tuple in [`link_config.py`](workstation/scripts/link_config.py), and `workstation/scripts/tests/test_readme_skills.py`, run by the pre-push hook, refuses a push when this table stops matching them.

| Skill | Scope | What it does |
|---|---|---|
| [`get-workstation-status`](skills/get-workstation-status/SKILL.md) | repo | Checks machine-specific prerequisites and workstation tools, reports versions, and gives recorded corrective actions. |
| [`setup-agents`](skills/setup-agents/SKILL.md) | repo | Assesses the workstation toolchain and sets up an engineer's AI coding assistants, confirming each choice, then applying shared instructions and skills or handing over commands. |
| [`ingest-source`](skills/ingest-source/SKILL.md) | repo | Adds a registered source to the knowledge base, filed under a predictable name and recorded in the catalogue for traceability. |
| [`fetch-to-markdown`](workstation/agent/skills/fetch-to-markdown/SKILL.md) | global | Converts web pages, PDFs or Office documents to clean markdown, routing each to the right tool and quality-checking the result. |
| [`verify-docs`](workstation/agent/skills/verify-docs/SKILL.md) | global | Audits documentation for stale claims by running a command that proves or refutes each, reporting them in an evidence table. |
| [`review`](workstation/agent/skills/review/SKILL.md) | global | Produces structured, read-only findings reports on documents or code, including regulatory texts and specs; applies fixes only when explicitly asked. |
| [`fix-findings`](workstation/agent/skills/fix-findings/SKILL.md) | global | Applies the most recent review's findings by following the review skill's Apply mode, escalating judgement calls instead of guessing them. |
| [`python-quality`](workstation/agent/skills/python-quality/SKILL.md) | global | Sets up code-quality checks for Python projects: linting, type checking, test coverage, complexity and dependency audits, calibrated to existing code. |
| [`pdf-deliverable`](workstation/agent/skills/pdf-deliverable/SKILL.md) | global | Turns markdown or HTML into PDFs, from working notes to formal documents meeting a required page layout or archival standard. |
| [`confluence-publish`](workstation/agent/skills/confluence-publish/SKILL.md) | global | Publishes Markdown to a Confluence Cloud page under a target page you name, with confluence-sync-md and md2conf. |
| [`confluence-export`](workstation/agent/skills/confluence-export/SKILL.md) | global | Retrieves Confluence pages, subtrees or spaces as Markdown with cme, previewing the destination for approval first. |
| [`setup-mcp-servers`](workstation/agent/skills/setup-mcp-servers/SKILL.md) | global | Guides safe setup of documented MCP servers, collecting non-secret choices and handing registration commands to the user. |
| [`session-signature`](workstation/agent/skills/session-signature/SKILL.md) | global | Stamps an output with a signature id — workstation, user, AI assistant and workbench versions, model, UTC time — or the full JSON as the extended signature. |

## Layout

``` txt
SOURCES.md                	the register — source of truth.   
SOURCE_CATALOGUE.md       	one-line capability summary per source.   
TODO.md                   	open work carried between sessions.   
AGENTS.md                 	instructions for agents working in this repo.   
CLAUDE.md                 	imports AGENTS.md for Claude Code — per clone, not in git.   
.agents/rules/            	imports AGENTS.md for Antigravity.   

docs/                     	the corpus — what the workbench reads.   
  landing-zone/           	ingested external sources     — not in git.   
  guidance/               	distilled agent-facing notes  — in git.   
    DEVELOPMENT-PLAN.md   	phased curriculum for agents  — in git.   
  presentations/          	Reveal.js decks about the workbench — in git.   

skills/                   	this repo's own skills — what the workbench does.   
  README.md               	the repo-local vs. global line, and how to load these.   
  get-workstation-status/ 	checks machine prerequisites and workstation tools.
  ingest-source/          	turns one register entry into a corpus file.   
  setup-agents/           	detects the machine's AI assistants and links the config for them.   

workstation/              	this machine's setup — serves the repo, never a deliverable.   
  README.md               	what each subfolder below is for.   
  dependencies.toml      	common external dependencies and readiness requirements.
  cli/README.md           	the CLI toolchain index.   
  cli/<tool>/             	per-tool CLI guidance         — authored files in git.   
  mcp/README.md           	the MCP server index.   
  mcp/<server>/           	per-server MCP guidance       — authored files in git.   
  agent/                  	agent config + global skills, symlinked into ~/.claude/.   
  machines/               	per-machine measured state and readiness profiles.
  scripts/                	the inventory probe, readiness report, link checker and other stdlib helpers.   
  validation/             	steps and fixtures that prove a machine works.   

scripts/                  	headless verify-docs runner.   
.github/workflows/        	weekly documentation audit — dormant on Azure DevOps.   
azure-pipelines/          	the same audit for Azure DevOps — written, not yet run.   

pyproject.toml            	Python project metadata.   
cliff.toml                	git-cliff config generating CHANGELOG.md from commits.   
VERSIONING.md             	the versioning policy and release steps.   
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
| [`docs/guidance/DEVELOPMENT-PLAN.md`](docs/guidance/DEVELOPMENT-PLAN.md) | **Roadmap.** Phased curriculum on agentic AI coding, Skills, MCP and SDD, each phase ending in a concrete artefact. Reading is marked ✓ (registered in `SOURCES.md`) or ➕ (not registered yet), so it doubles as a prioritised ingestion backlog. Neither marker says whether the file is on disk. |
| [`workstation/cli/README.md`](workstation/cli/README.md) | **CLI tool index.** What each per-tool file is for, a `command → product → folder` map, and the version-currency rule. |
| [`workstation/mcp/README.md`](workstation/mcp/README.md) | **MCP server index.** The third-party servers configured into this machine, and the file contract they follow. |
| [`workstation/machines/README.md`](workstation/machines/README.md) | **Machine index.** One file per machine this workbench runs on, and the test for whether a fact is policy, a route, or machine state. |
| [`AGENTS.md`](AGENTS.md) | **Agent instructions for this repo** — the invariants for working in the files this README describes, the layer model, the ingestion invariant, and the rule that GitHub sources are fetched as raw READMEs rather than cloned. Read directly by GitHub Copilot; Claude Code reaches it through `CLAUDE.md`, written per clone by the install command above, and Antigravity through [`.agents/rules/workbench.md`](.agents/rules/workbench.md), each a one-line `@AGENTS.md` import. |

## The workstation — `workstation/`

What the workbench runs on — the machines, not an architecture.

**[`workstation/README.md`](workstation/README.md) is the map** — what each subfolder holds, where to start in it, and the rules spanning all of them. The summary:

| Path | Role |
|---|---|
| [`workstation/cli/`](workstation/cli/README.md) | The CLI toolchain. One folder per tool: authored `install.md` and `quick_start.md`, plus an ingested `reference.md`. Read `quick_start.md` before invoking a tool you haven't used this session. |
| [`workstation/mcp/`](workstation/mcp/README.md) | Third-party MCP servers. One folder per server: authored `setup.md` plus an ingested `reference.md`. |
| [`workstation/machines/`](workstation/machines/README.md) | One file per machine: paths, shell, which tools actually run, what is broken. **The only place a machine-specific fact belongs.** |
| [`workstation/scripts/`](workstation/scripts/README.md) | Scripts maintaining this tree. `inventory.py` probes the toolchain and generates a machine's tool table; `status.py` reports whether the machine meets its prerequisites; `link_config.py` reports or repairs the `~/.claude` links and, with `--agent copilot`, the global instruction and skill links under `~/.copilot`. All three are read-only unless told otherwise. `databricks_mcp.py` prints the Claude Code and Copilot CLI registration commands for the Databricks MCP services, and runs none of them. `bump_frontmatter_version.py` reports (or, with `--apply`, writes) the `version:` frontmatter field across skills, guides, machine notes and key documents to match a new release; see [`VERSIONING.md`](VERSIONING.md). `settings_delta.py` prints what the live `~/.claude/settings.json` lacks from the repo's reference copy, for the hand merge. |
| `workstation/agent/` | Claude Code and GitHub Copilot configuration, **linked into `~/.claude/` and `~/.copilot/`** so it is versioned rather than scattered across a home directory. See below. |

**The split is by lifetime, not by platform** — policy, route and machine state live in different
files. [`workstation/machines/README.md`](workstation/machines/README.md) has the table and the test.

### `workstation/agent/`

Edits to `~/.claude/CLAUDE.md` or the `review` skill land here, because those paths are links into this directory.

**Everything here is shared by every machine, unmodified.** Anything machine-specific goes in `workstation/machines/`; anything machine-*local* and not compliance-bound goes in `~/.claude/settings.local.json`, which is untracked by design.

| Path | Role |
|---|---|
| `workstation/agent/README.md` | The contract: what is linked where, and what is deliberately left untracked. |
| `workstation/agent/setup/<platform>.md` | Per-platform setup for a new machine. macOS uses symlinks; Windows uses junctions and hardlinks, because symlinks there need admin. |
| `workstation/agent/AGENT-INSTRUCTIONS.md` | Global instructions applying to every project — linked to `~/.claude/CLAUDE.md` and `~/.copilot/copilot-instructions.md`. Policy only, no platform, no paths. |
| `workstation/agent/settings.json` | Reference copy of the shared Claude Code settings — **merged into `~/.claude/settings.json` by hand, never linked.** [Why, and the procedure](workstation/agent/README.md#settings-are-merged-never-linked). |
| `workstation/agent/skills/<skill>/` | The skills promoted to global scope, each linked to `~/.claude/skills/<skill>`. Which skills those are is [`link_config.py`](workstation/scripts/link_config.py)'s `SKILLS` tuple — see [`skills/README.md`](skills/README.md). A skill earns promotion here by working in a repo that is not this one; until then it stays in [`skills/`](skills/). `SKILL.md` is a skill's definition; `scripts/` and `tests/` hold its repeatable actions. |

Because these are links into a git repo, check `git status` here before overwriting or regenerating any of them — and if this directory is ever moved or renamed, **repoint the links**, or every session silently loses its global instructions. On Windows `CLAUDE.md`, `machine.md`, and Copilot's `copilot-instructions.md` are hardlinks and any atomic-saving editor severs them silently; [`workstation/agent/setup/windows.md`](workstation/agent/setup/windows.md) carries the detection command.

## Presentations — `docs/presentations/`

Reveal.js decks about the workbench, one folder per deck. They are hand-edited HTML: nothing to
install or build to view them.

| Path | Role |
|---|---|
| `docs/presentations/vendor/reveal.js/<version>/` | The Reveal.js release every deck loads — core, the highlight, notes, zoom and search plugins, and its MIT licence. Third-party, committed so decks run offline; never hand-edit it. |
| `docs/presentations/fetch-reveal.sh` | Fetches one Reveal.js release from cdnjs into `vendor/reveal.js/<version>/`. |
| `docs/presentations/workbench-briefing/index.html` | The info-session deck: one `<section>` per slide, a nested `<section>` for a vertical stack, `<aside class="notes">` for speaker notes. |
| `docs/presentations/workbench-briefing/theme.css` | Colours, fonts, backgrounds and code-block styling for that deck. |
| `docs/presentations/workbench-briefing/build-artifact.sh` | Builds a copy for publishing as a claude.ai Artifact, and warns when npm has a newer Reveal.js release than the vendored one. |

**View:** open `index.html` in a browser (`open docs/presentations/workbench-briefing/index.html` on
macOS, `start` on Windows). Reveal.js loads from `vendor/`, so it works offline; only the fonts come
from Google Fonts, and fall back to system fonts without internet. Press `Esc` for the overview, `S`
for speaker notes; the deck's last slide lists the other keys.

**Update the deck:** edit `index.html` or `theme.css` and reload the browser. To refresh the
published Artifact, run `sh docs/presentations/workbench-briefing/build-artifact.sh <out-dir>` and
publish `<out-dir>/workbench-deck.html` with `reveal.css` and `theme.css` beside it.

**Upgrade Reveal.js** when the build warns that a newer release exists:
`sh docs/presentations/fetch-reveal.sh <version>`, change the version in the deck's `index.html`
paths, check every slide, then delete the old `vendor/reveal.js/<old-version>/` folder. A major
version can change behaviour, so it is a deliberate step, never part of a build.

Both scripts need `sh`, `sed`, `grep` and `curl`: present on macOS; on Windows run them from Git Bash.

## Repo mechanics

| Path | Role |
|---|---|
| [`skills/README.md`](skills/README.md) | Index of this repo's own skills, the line dividing them from the global ones in `workstation/agent/skills/`, and the per-clone links that make them load — Claude Code and Copilot discover `.claude/skills/`, not `skills/`. |
| `pyproject.toml` | Project metadata. No runtime dependencies; the `dev` dependency group supplies `pytest`, `ruff` and `pyright` for repository quality checks, and `git-cliff` for the changelog. |
| `.python-version` | Pins the interpreter for `uv` — currently 3.14. |
| `.verify-claims-allow` | Path claims the documentation gate is to leave alone, one glob per line with a reason above each. Repo-local on purpose: the pre-push hook is shared by every repo that links it, so exemptions must not travel with it. |
| `.verify-flags-allow` | Its sibling for flag claims, one `<command> <flag>` per line: a flag that works but that no help text documents, such as `git diff --staged`. It only ever downgrades a refutation. |
| `.pre-push-tests` | Unit-test directories the pre-push hook runs before a push, one per line. Repo-local for the same reason. |
| `.pre-push-ruff` | Its presence makes the pre-push hook run `ruff check` and `ruff format --check`. Repo-local for the same reason. |
| `.pre-push-pyright` | Its presence makes the pre-push hook run the venv interpreter with `-m pyright`. Repo-local for the same reason. |
| `.gitignore` | Excludes the ingested corpus, the per-clone `.claude/` and `CLAUDE.md`, `.venv/`, `.DS_Store`, and Python build artefacts. |
| `.github/workflows/verify-docs.yml` | Weekly documentation audit on GitHub Actions, opening a pull request with the reports. **Dormant:** the repo is hosted on Azure DevOps, where it does not run — its port is the next row. |
| `azure-pipelines/verify-docs.yml` | The same weekly audit for Azure DevOps, opening a pull request with `az repos pr create`. Its header lists the one-time setup in ADO. **Written, not yet run** — [`TODO.md`](TODO.md) #9. |
| `scripts/verify-docs.sh` | Headless `verify-docs` run through `claude -p`, writing a report and editing no documentation. Called by the dormant workflow above; runnable by hand with `ANTHROPIC_API_KEY` set. |
| [`cliff.toml`](cliff.toml) | git-cliff configuration: how commits are grouped into `CHANGELOG.md` and how the next version is suggested. Tune this file, not the generated changelog. |
| [`VERSIONING.md`](VERSIONING.md) | The versioning policy — SemVer 2.0.0, Conventional Commits, the public API table — and the steps to cut a release. |

## Versioning

This repository follows [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html). One
version for the whole repository — workstation scripts, skills and the agent harness together —
`[project] version` in [`pyproject.toml`](pyproject.toml) is the source of truth, released as an
annotated tag `vX.Y.Z`. `CHANGELOG.md` is **generated** by [git-cliff](https://git-cliff.org) from
[`cliff.toml`](cliff.toml); it is never edited by hand.

Commits follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):
`type(scope)!: summary`, e.g. `feat(skills): add the python-quality skill`. While the repository is
at `0.x`, a `feat` or a breaking change (`!`) bumps MINOR and anything else bumps PATCH; a breaking
change is still marked **BREAKING** in the changelog.

The full policy — the public API table defining what counts as breaking, the road to `1.0.0`, and
the exact release steps — is in [`VERSIONING.md`](VERSIONING.md). `git-cliff` is a `dev`-group
dependency, installed by `uv sync` like the rest of the toolchain; no release has been tagged yet —
see [`TODO.md`](TODO.md).

## What is tracked in git

Everything authored is tracked; the ingested third-party corpus is not, so a fresh clone's corpus is empty by design. [`AGENTS.md` § *The corpus is not in git*](AGENTS.md#the-corpus-is-not-in-git) has what is excluded and when to rebuild.
