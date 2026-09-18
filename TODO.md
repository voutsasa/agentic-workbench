---
role: Open work carried between sessions — committed new work and unproven existing gaps
updated: 2026-09-18
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

### 2. `fetch-to-markdown` has two routes proven of five

Opened 2026-09-13. Server-rendered HTML is proven against rdi.berkeley.edu/llm-agents/f24 — that run
is what found the `<table>` and relative-link defects the skill now guards against. The raw README
route was proven on 2026-09-15 by angular-eslint, whose relative links had to be resolved against
`blob/main/` before the link check passed.

| Route | State |
|---|---|
| Server-rendered HTML → extractor → pandoc | **proven** |
| `github.com/<owner>/<repo>` → raw README | **proven** — angular-eslint, 2026-09-15 |
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
`%APPDATA%\Code\User\settings.json`, a Chat session lists the instruction file in its loaded context,
`detect.py` reports `true`, and the machine note records it. The agent does not make the edit —
settings files are the user's.

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
`/opt/homebrew/Caskroom/copilot-cli/1.0.24/copilot`, while `copilot --version` reported 1.0.63 that
day and **1.0.83 on 2026-09-14**, with the path unchanged. Homebrew did not do it: `brew info --cask
--json=v2 copilot-cli` still reports `"installed": "1.0.24"`, and marks the cask `"auto_updates": true`.
So the CLI updates itself, outside the cask — `autoUpdate` defaults to `true` (`copilot help config`) —
but where the running version actually lives was never found. Until it is, a `brew upgrade` and the
CLI's own updater may be managing two copies, and `inventory.py`-style path checks read the wrong one.

**Closes when:** the executable path of the running version — read from `copilot --version` at the
time, since it moves on its own — is found and quoted in
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
| Copilot CLI | reads `AGENTS.md` **and** `CLAUDE.md` | **double load removed 2026-09-16, unproven.** `CLAUDE.md` is now gitignored and written only by `link_config.py --claude-md`, so a Copilot-only clone matches run C below. A clone running both assistants still loads twice, as run B |
| Antigravity | `.agents/rules/workbench.md` → `@AGENTS.md` | **unproven.** Whether the rule is set to **Always On** and applies, and whether Antigravity also reads `AGENTS.md` natively — its rules page does not mention it |

**Copilot's double load, as measured before `CLAUDE.md` was untracked.** Copilot CLI 1.0.83 on the macOS workstation,
`/context` as the first command of a fresh session, System Prompt line:

| Run | Setup | System Prompt |
|---|---|---|
| A | `copilot --no-custom-instructions` | 9.3k |
| B | `AGENTS.md` + `CLAUDE.md` importing it | 16.2k |
| C | `AGENTS.md` only (`CLAUDE.md` moved aside) | 12.8k |

One copy is C − A = 3.5k; B − A = 6.9k is two. Copilot's docs dedupe "identical" instruction files, and
a one-line import is not identical. The duplicate is identical text, so it cannot conflict, and costs
3.5k of a 1M context. It was first accepted, because every route below that would remove it was
checked and is worse. The route taken instead is **not tracking `CLAUDE.md` at all**: each clone
writes it with `link_config.py --claude-md --apply` only when Claude Code runs there, so the cost
falls only on clones that use both assistants.

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
files; `/context` as the first command of Copilot CLI in a clone set up without `--claude-md` shows
the System Prompt at run C's size, not run B's; and Antigravity, with the rule set to **Always On**, shows the rule applied to a session —
each observation recorded in the machine note.

### 11. `verify_claims.py` has four Pyright errors

Opened 2026-09-18, found while fixing the man-page overstrike defect (`7b0daf4`) and left unfixed as
outside that change. None fails a test or the pre-push gate today.

| Location | Error | Consequence |
|---|---|---|
| `workstation/agent/skills/verify-docs/scripts/verify_claims.py:419-420` | `help_subject` returns `("no-script", [])` against a declared `tuple[list[str], str] \| None` | a sentinel smuggled through the return type; callers must special-case it with nothing checking that they do |
| same file, L839 and L882 | an exception object passed to `clip(text: str)` | works because `clip` calls `str()`; the annotation is wrong |
| same file, L1079 | `import certifi` unresolved in this repo's `.venv` | only the TLS-advice path reaches it; unproven whether it degrades cleanly |

**Closes when:** `.venv/bin/pyright workstation/agent/skills/verify-docs/scripts/verify_claims.py`
reports 0 errors (pyright is not yet in this repo's venv — adding it is the user's install) and the
verify-docs suite still passes.

### 12. `review`'s Apply mode changes have not run on a real review

Opened 2026-09-18, with `5949ef5`. Approve-each (step 2), failing-test-first (step 4) and recording
unfixed findings (step 8) exist only as prose; the unit tests cover `repo_check.py`, not the procedure.

**Closes when:** one review in Apply mode on a code target uses approve-each, shows a regression test
failing before its fix, and records an unapplied finding in that repo's TODO file.

### 14. The ruff post-edit hook is unproven on Windows and under `COPILOT_HOME`

Opened 2026-09-18, with `workstation/agent/hooks/ruff_on_edit.py`. Proven on macOS the same day: it
fires in Claude Code (`Write`) and in Copilot CLI (`create`), each leaving a `.py` file ruff-formatted
— both runs recorded in `workstation/machines/macos-workstation.md`. Still unproven:

| Unproven | Why it could differ |
|---|---|
| Windows | both registrations are `bash` with `.venv/bin/python`; Copilot's `powershell` field is not set, and a Windows venv has `Scripts\python.exe` |
| Copilot's `edit` tool | only `create` was observed; `edit` is assumed to carry the path under the same key |

**Closes when:** a `.py` edit on the Windows machine is formatted by the hook in each assistant, or the
hook is documented as POSIX-only; and a Copilot `edit` of an existing file is observed formatted.

### 15. The trigger-based *Design before build* and the subagent rule have not steered a session

Opened 2026-09-18, with the rewrite of principle 5 in `workstation/agent/AGENT-INSTRUCTIONS.md`
(divergence, effort, impact, plus the mid-course checkpoint) and, the same day, the subagent rule in §
*Skills and subagents* (spawn without asking only for deterministic or designed-and-approved work, or
a bounded thinking task). Both load from the next session on; no session has yet run under them.

**Closes when:** one later session is observed proceeding without asking on work that meets no
trigger and stopping on one that does, and spawning a subagent under the new rule whose result the
parent re-checks — each case and call recorded here or in the machine note.

### 16. The Windows machine note predates six skills, the hooks key, Copilot and `typst`

Opened 2026-09-18, from the review of `workstation/`. `windows-ema-pf5n4xe7.md` § *Claude Code config*
records four skills and *6 of 6 linked*, while `link_config.py`'s `SKILLS` tuple now holds six and
`machine.md` is now linked for Copilot too. Its settings table has no row for the `hooks` key in
`workstation/agent/settings.json`, and its live `env` still carries the deprecated
`ANTHROPIC_SMALL_FAST_MODEL`. The *Two installs are behind* table compares against a version
"recorded" in `install.md`, which `install.md` no longer carries. `typst` was added to the toolchain
the same day and has never been probed there.

**Closes when:** on the Windows machine, `python workstation\scripts\link_config.py --agent claude
--agent copilot` and `python workstation\scripts\inventory.py --host ema-pf5n4xe7` are run and their
output replaces the two tables; the settings table gains the `hooks` row with its measured state; and
the version comparison is restated against the machine's own earlier measurement or removed.

### 17. The 2026-09-18 instruction changes have not steered a session outside this repo

Opened 2026-09-18, from the review of `workstation/agent/AGENT-INSTRUCTIONS.md`. New that day:
`workstation/…` paths resolve against the machine note's `repo:` field, `~/.claude/machine.md` is
read by Copilot too, the settings rule covers `~/.copilot/settings.json`, the overwrite gate excludes
ordinary edits, and plan mode, effort and model tiers are named. `~/.copilot/copilot-instructions.md`
was linked on this machine the same day and not yet seen in a Copilot session.

One review finding was left unapplied, as low confidence: the file carries about thirty bold or
"never" emphases, which may make current models apply rules too broadly. That is a judgement, not a
measurement.

**Closes when:** a Claude Code session and a Copilot CLI session, each started in a repo other than
this one, read a `workstation/cli/<tool>/quick_start.md` through the `repo:` path without searching,
and `/context` in the Copilot session lists the user-level instructions — both recorded in
`workstation/machines/macos-workstation.md`. The emphasis finding closes when a session is observed
over-applying a rule because of it (then trim), or after a month of sessions without such a case
(then drop).

## Closed

Nothing yet. An item moves here with the evidence that closed it, or is deleted outright; a list of
things that turned out fine is not worth carrying.
