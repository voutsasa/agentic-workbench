---
role: Open work carried between sessions — committed new work and unproven existing gaps
updated: 2026-09-14
verified: never
---

# TODO

Work that is known-outstanding rather than merely imagined. The list holds two kinds of item: **new
work** that has been committed to but not yet built, and **existing gaps** — something already written
that no run has proven. Each item says what would close it, so a cold session can act without
reconstructing the reasoning.

**An item earns a place here if it is committed new work or an unproven gap.** An idea nobody has
committed to belongs in a conversation. Delete an item when its evidence exists — a passing command, a
converted file, a pipeline run — and not when it merely feels handled.

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

### 8. The running Copilot CLI is not the one its path names

Opened 2026-09-13, on the macOS workstation. `readlink -f /opt/homebrew/bin/copilot` resolves to
`/opt/homebrew/Caskroom/copilot-cli/1.0.24/copilot`, while `copilot --version` reports 1.0.63.
`autoUpdate` defaults to `true` (`copilot help config`), which fits an update installed outside the
cask, but where 1.0.63 actually lives was never found. Until it is, a `brew upgrade` and the CLI's
own updater may be managing two copies, and `inventory.py`-style path checks read the wrong one.

**Closes when:** the executable path of the running 1.0.63 is found and quoted in
`workstation/machines/macos-workstation.md` (its *Copilot CLI* section), together with which of the
two updaters owns it. The agent records; any upgrade or cleanup is the user's to run.

### 9. No Azure DevOps pipeline exists beside the GitHub one

Opened 2026-09-14. The only pipeline is `.github/workflows/verify-docs.yml`, and it only runs on
GitHub — while this clone's only remote, `emaea`, is an Azure DevOps repo, so the audit never runs for
it. Several of its steps have no ADO equivalent as written. The counterparts below were checked against
Microsoft Learn on 2026-09-14; none has run yet:

| GitHub-specific | ADO counterpart to prove |
|---|---|
| `actions/checkout` with `fetch-depth: 0` | `checkout: self` with `fetchDepth: 0` (fetches all history) and `persistCredentials: true`, so the later `git push` authenticates |
| `setup-python` reading `python-version-file: .python-version` | `UsePythonVersion@0` — it has no version-file input and `versionSpec` is required, so a script step must read `.python-version` first |
| `setup-node` | `UseNode@1` with `version: '22'` |
| `secrets.ANTHROPIC_API_KEY` | a secret pipeline variable or variable group — secrets are not decrypted into the environment, so each step must map it under `env:` |
| `gh pr create` with `GITHUB_TOKEN` | `az repos pr create` (the `azure-devops` CLI extension), authenticated by `AZURE_DEVOPS_EXT_PAT: $(System.AccessToken)` |
| workflow `permissions: contents/pull-requests: write` | on the repo, `<project> Build Service (<org>)` needs *Contribute*, *Create branch* and *Contribute to pull requests* — or `Project Collection Build Service (<org>)` if the job authorization scope is collection |

**Closes when:** an `azure-pipelines/verify-docs.yml` (or agreed path) has run once on an ADO
project, both reports were produced, and either a pull request was opened or the run logged *No
documentation drift found* — with the run URL recorded here before the item is deleted.

### 10. `AGENTS.md` has not been seen loading in Claude Code or Antigravity

Opened 2026-09-14, when `CLAUDE.md` became `AGENTS.md` plus one-line `@AGENTS.md` imports.

| Assistant | Route | State |
|---|---|---|
| Claude Code | `CLAUDE.md` → `@AGENTS.md` | **unproven in this repo.** The mechanism is observed: in a scratch folder, Claude Code 2.1.270 quoted a marker that existed only in the imported `AGENTS.md` |
| Copilot CLI | reads `AGENTS.md` **and** `CLAUDE.md` | **measured: loads it twice, accepted.** See below |
| Antigravity | `.agents/rules/workbench.md` → `@AGENTS.md` | **unproven.** Whether the rule is set to **Always On** and applies, and whether Antigravity also reads `AGENTS.md` natively — its rules page does not mention it |

**Copilot's double load is accepted, not open.** Copilot CLI 1.0.83 on the macOS workstation,
`/context` as the first command of a fresh session, System Prompt line:

| Run | Setup | System Prompt |
|---|---|---|
| A | `copilot --no-custom-instructions` | 9.3k |
| B | `AGENTS.md` + `CLAUDE.md` importing it | 16.2k |
| C | `AGENTS.md` only (`CLAUDE.md` moved aside) | 12.8k |

One copy is C − A = 3.5k; B − A = 6.9k is two. Copilot's docs dedupe "identical" instruction files, and
a one-line import is not identical. The duplicate is identical text, so it cannot conflict, and costs
3.5k of a 1M context. Every route that would remove it was checked and is worse:

| Route | Why not |
|---|---|
| `ln -s AGENTS.md CLAUDE.md` | the Windows clone has `core.symlinks=false` (`workstation/machines/windows-ema-pf5n4xe7.md`), so it checks out as a text file |
| Import from `.claude/rules/agents.md` | the rule loads but its `@AGENTS.md` does not expand — scratch test, Claude Code 2.1.270 — and `.gitignore` excludes `.claude/` |
| Import from a committed `CLAUDE.local.md` | it expands, but Anthropic documents the file as personal and gitignored, so it would collide with anyone's own notes |
| A Claude Code setting naming `AGENTS.md` | none exists; the memory page says "Claude Code reads `CLAUDE.md`, not `AGENTS.md`" |
| `SessionStart` hook printing `AGENTS.md` | hook output is capped at 10,000 characters and `AGENTS.md` is 12,264 |
| `--append-system-prompt-file AGENTS.md` | a per-launch flag, so every launch has to remember it |

Revisit only if Copilot starts deduplicating imports or Claude Code gains a setting for the file name.

**Closes when:** `/context` in a fresh Claude Code session in this repo lists `AGENTS.md` under Memory
files, and Antigravity, with the rule set to **Always On**, shows the rule applied to a session —
each observation recorded in the machine note.

## Closed

Nothing yet. An item moves here with the evidence that closed it, or is deleted outright; a list of
things that turned out fine is not worth carrying.
