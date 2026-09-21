---
role: Open work carried between sessions — committed new work and unproven existing gaps
updated: 2026-09-21
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

### 22. The pre-push hook does not echo the flag exemptions in force

Opened 2026-09-21, with `.verify-flags-allow`. The hook reads `.verify-claims-allow` itself and prints
*"N path exemption(s)"* before it runs, on the principle that an exemption nobody sees is one nobody
revisits (`review/scripts/pre-push:177-181`). The new flag file gets no such line: `verify_claims.py`
reads it directly, so the exemption applies on a push but is invisible in the hook's output.

Not fixed in the same commit on purpose — the hook is a shared pre-push gate in the globally symlinked
skills tree, which is a *Design before build* impact trigger. The design and its alternatives are the
user's to settle.

**Closes when:** either the hook prints the flag exemptions in force on a real push from a machine where
it is installed, or the user records here that the file's visibility in a diff is enough and this item
goes.

### 21. The `pre-push` gate is not installed on `ema-pf5n4xe7`

Opened 2026-09-21, found while pushing this session's four commits. `.git/hooks/` in this clone holds
only the fourteen `.sample` files git ships, so **every push from this machine runs no gate**. The
machine note had claimed the hook was installed as a copy, verified 26 August; that claim is now
corrected in place.

The push itself is not unchecked work — `repo_check.py`, all seven `.pre-push-tests` suites and both
`ruff` commands were run by hand and passed. But the gate that makes that automatic is absent, and the
hook would have **refused** that push: one of the three refuted claims of item 19, now closed below, was
in `workstation/agent/skills/review/SKILL.md`, which the push touched.

Installing it is the user's — it changes their local git state, and it must be a copy rather than a link
because git will not run a hook through a junction:

```powershell
Copy-Item workstation\agent\skills\review\scripts\pre-push .git\hooks\pre-push -Force
```

**Closes when:** the hook is in place and has been observed running on a real push from this machine.

### 20. The corpus is near-empty on this machine — 1 of 76 entries ingested

Opened 2026-09-21, measured rather than estimated: `repo_check.py --corpus` reported **0 of 76** and
`docs/landing-zone/` did not exist at all. Nothing had recorded that state, while
[`README.md`](README.md) advertises the ingestion pipeline as a core capability. Absent is not broken —
the corpus is gitignored and rebuilt from [`SOURCES.md`](SOURCES.md) on request — but it being
unrecorded was.

The "delta" here is the whole register, so this is a full ingestion run, not a top-up. The preflight and
the progress ledger a batch resumes from now exist as `repo_check.py --corpus --json`, one row per entry
with its resolved destination.

**One source has been ingested end to end to validate the route before the set**, per *start small*:
`SOLID Relevance` (§2, a server-rendered Jekyll blog post) through the
server-rendered route — curl, `extract_article.py` on the `div.blog-post` node, `pandoc -f html -t gfm`,
`add_frontmatter.py`. All four quality checks passed on this machine: markup-noise count 0, no relative
link targets, headings and the blockquote intact, and the file ends on the post's own last paragraph.
The ledger moved to **1 of 76**. The remaining 75 are a deliberate long operation, the user's to
schedule.

**Closes when:** `repo_check.py --corpus` reports every entry present, or the user records a smaller
target here and that target is met.

### 9. The Azure DevOps pipeline has never run

Opened 2026-09-14: the only pipeline was `.github/workflows/verify-docs.yml`, which never runs for this
clone's only remote — `origin`, `https://euemadev@dev.azure.com/euemadev/EA/_git/agentic-workbench`, an
Azure DevOps repo (it was recorded here as named `emaea`; `git remote -v` on 2026-09-21 says `origin`). **Written 2026-09-19** as
`azure-pipelines/verify-docs.yml`, applying every counterpart below; checked only locally — the YAML
parses into the ten intended steps, and the pull-request step passes `bash -n`. Its header carries
the three one-time setup steps in ADO, which are the user's. The counterparts were checked against
Microsoft Learn on 2026-09-14; none has run yet:

| GitHub-specific | ADO counterpart, as written |
|---|---|
| `actions/checkout` with `fetch-depth: 0` | `checkout: self` with `fetchDepth: 0` (fetches all history) and `persistCredentials: true`, so the later `git push` authenticates |
| `setup-python` reading `python-version-file: .python-version` | `UsePythonVersion@0` — it has no version-file input and `versionSpec` is required, so a script step must read `.python-version` first |
| `setup-node` | `UseNode@1` with `version: '22'` |
| `secrets.ANTHROPIC_API_KEY` | a secret pipeline variable or variable group — secrets are not decrypted into the environment, so each step must map it under `env:` |
| `gh pr create` with `GITHUB_TOKEN` | `az repos pr create` (the `azure-devops` CLI extension), authenticated by `AZURE_DEVOPS_EXT_PAT: $(System.AccessToken)` |
| workflow `permissions: contents/pull-requests: write` | on the repo, `<project> Build Service (<org>)` needs *Contribute*, *Create branch* and *Contribute to pull requests* — or `Project Collection Build Service (<org>)` if the job authorization scope is collection |

**Closes when:** the user has done the header's setup and `azure-pipelines/verify-docs.yml` has run
once on the ADO project, both reports were produced, and either a pull request was opened or the run logged *No
documentation drift found* — with the run URL recorded here before the item is deleted.

### 12. `review`'s Apply mode approve-each step has not run

Opened 2026-09-18, with `5949ef5`. Narrowed the same day: the review of `workstation/` applied in
`e9b3263` exercised failing-test-first (step 4) — `test_link_config.py` failed with 2 failures and 1
error against the unfixed `link_config.py` before the fix — and recording unfixed findings (step 8),
into this file's items 16 and 17. Approve-each (step 2) did not run: the user answered the review's
decisions and then said to go ahead with all of it.

**Closes when:** one review in Apply mode, with the user asking to approve each finding, offers one
choice per finding with its confidence and applies only the approved ones.

### 15. The subagent rule has not steered a session

Opened 2026-09-18, with the rewrite of principle 5 in `workstation/agent/AGENT-INSTRUCTIONS.md` and
the subagent rule in § *Skills and subagents*. **Principle 5's triggers were observed on 2026-09-19**
in a fresh Claude Code session in a scratch repo (`~/tmp/probe-repo`): it fixed a README typo without
asking, and on *add a git pre-commit hook that runs ruff* it stopped, named the hook as a gate needing
design approval, and handed over the `uv` scaffolding commands instead of running them.

Also seen in that session, twice: a bare one-line request was read as pasted text with "no message of
your own" and the agent asked before acting — on a read-only lookup, which meets no trigger. The typo
request between them was acted on. Two samples; not yet a reason to change the instructions.

**Closes when:** a session spawns a subagent under the rule and the parent re-checks its result,
recorded here or in the machine note. The pasted-text reading is dropped after a month of sessions
without it, or becomes an instruction change if it recurs.

### 17. The emphasis in `AGENT-INSTRUCTIONS.md` may be over-applied

Opened 2026-09-18, from the review of `workstation/agent/AGENT-INSTRUCTIONS.md`, as the unapplied
low-confidence finding: the file carries about thirty bold or "never" emphases, which may make
current models apply rules too broadly. That is a judgement, not a measurement.

The rest of that item closed on 2026-09-19: both assistants resolved a `workstation/…` path through
the machine note's `repo:` field from outside this repo, without searching — recorded in
`workstation/machines/macos-workstation.md`.

**Closes when:** a session is observed over-applying a rule because of the emphasis (then trim), or
after a month of sessions without such a case (then drop).

## Closed

### 19. `verify_claims.py` refused a push over two git flag claims

Opened 2026-09-21 from the repo review, closed the same day. `verify_claims.py --repo .` exited 1 with 3
refuted rows, all three about a git flag that works. Two gaps, both now in the checker with unit tests:

| Gap | Fix | Test |
|---|---|---|
| a flag git's abbreviated help prints in optional-negation bracket form was substring-searched for its plain spelling, and missed | `bracket_negation_re` and `flag_line`, tried on every rung of the help ladder after the plain match. Only that one form, only the flag's own stem | `TestBracketNegationInHelp`, 5 tests |
| a working synonym that no abbreviated help prints at all, which no help parsing can reach | `.verify-flags-allow` at the repo root, one `<command> <flag>` per line — bound to the whole command, checked last so it only downgrades a refutation, and a line naming no flag exempts nothing | `TestFlagExemptions`, 6 tests |

Closing evidence: `verify_claims.py --repo .` reports **0 refuted** over roughly 1,320 claims, prints
*No claim was refuted*, and exits 0. Only the refuted count and the exit code are recorded — the verified
and unverifiable totals move with every markdown edit, including this one.

A third gap was recorded here and was not one. Two docling flag claims were getting different verdicts
between a scoped and a full run, which read as a verifier defect. It was two defects of this repo's own
making: the probe timeout was 20 seconds while `docling` takes 17s to answer `--version` and 20s to answer
`--help`, so the verdict turned on machine load (both timeouts are now 120s); and two documents wrote a
`docling convert` flag as though it were a bare `docling` flag, which the verifier was right to refuse
(`windows-ema-pf5n4xe7.md:394`, and line 9 of
[`workstation/cli/tesseract/quick_start.md`](workstation/cli/tesseract/quick_start.md) — both corrected).
The verifier already probes a subcommand's own help when the line names the subcommand, so there was
nothing to build.

### 5. The Copilot and project links were unproven on Windows

Opened 2026-09-13. Closed 2026-09-21. All three rows directly exercised on `ema-pf5n4xe7`:
`link_config.py --project --claude-md --agent claude --agent copilot --apply --force` linked
`project/skills/ingest-source` and `project/skills/setup-agents` as directory junctions in
`.claude\skills` (2 of 2) and `project/CLAUDE.md`; Copilot's global skills and
`~/.copilot/copilot-instructions.md` are 8 of 8 linked, and Copilot CLI was observed actually loading
that file (its own responses started following `AGENTS.md`'s `Claim | Command + output | Status`
convention unprompted, and VS Code's Chat Debug View showed it as a request attachment); `detect.py`
run directly found VS Code via `~\scoop\apps\vscode\current\bin\code.CMD`, version 1.138.0, resolving
the `.cmd` shim correctly. Sections A–E of `workstation/validation/windows.md` all ran, with results in
`workstation/machines/windows-ema-pf5n4xe7.md`. Its two *Unknown on Windows* notes: `render_page.py`'s
exit-2 interpreter naming is now confirmed correct (and a real bug found and fixed alongside it, see
item 14's sibling fix in `render_page.py`); docling's byte-identity with macOS's output is still
unchecked — no macOS copy exists to diff against, and nobody has committed to producing one.

### 18. Playwright's Chromium browser binary was missing on Windows

Opened 2026-09-21, found while closing item 5. Closed the same day. `render_page.py` imported
`playwright` fine through the pipx venv, but `BrowserType.launch` failed — `chrome-headless-shell.exe`
was missing under `~\AppData\Local\ms-playwright\`. Fixed by the user:
`& "C:\Users\voutsas\AppData\Local\pipx\pipx\venvs\playwright\Scripts\python.exe" -m playwright install
chromium`. Re-verified end to end: `render_page.py` on `retirejs.github.io/retire.js/` wrote 224 KB of
rendered HTML; `defuddle` turned it into a 15,137-word body against the 206-word raw fetch, with the
real page title `"Retire.js"`. Validation section D is now fully closed.

### 14. The ruff post-edit hook — Windows and Copilot's `apply_patch`

Opened 2026-09-18. Closed 2026-09-21 on `ema-pf5n4xe7`. Claude Code: a `Write` of an unformatted `.py`
file was reformatted by the hook (`import os` removed, spacing normalized) — the `.venv/Scripts/python.exe`
branch of the registration works as written; no change needed.

Copilot CLI: found broken, not just unproven. Debug logs (`--log-level debug`) showed Copilot edits an
*existing* file via a tool named `apply_patch`, not `edit` — the registered matcher `"edit|create"`
never matched it, and `apply_patch`'s `toolArgs` is a raw patch body
(`*** Update File: <path>`), not JSON, so `edited_path()`'s `json.loads` failed and returned `None`
before a matcher fix would even have mattered. Fixed both: the matcher now reads
`"edit|create|apply_patch"` (`ruff-on-edit.copilot.json`), and `edited_path()` gained a regex fallback
for the patch-body format (`ruff_on_edit.py`), with two new unit tests. Verified end to end: a captured
`apply_patch` call carrying `import   sys` / `def g( ):` / `return   sys.argv` (bad spacing, as
instructed) resulted in a file on disk reading `import sys` / `def g():` / `return sys.argv` with
correct PEP8 blank lines — output only ruff's formatter would produce from that patch, not the model.
17/17 unit tests pass.

### 16. VS Code has never been launched on the Windows machine

Opened 2026-09-18, narrowed 2026-09-21, closed 2026-09-21. `windows-ema-pf5n4xe7.md` was rewritten this
session from a live `link_config.py --agent claude --agent copilot --apply --force` (15 of 15 linked —
three files were `diverged`, triaged by diff, then forced) and `inventory.py --host ema-pf5n4xe7` (12 of
13 usable; `defuddle`, `tesseract`, `weasyprint` cleared since 14 September, `typst` now probed and
absent). The settings table gained the `hooks` row, read from the live `~/.claude/settings.json`, and
the `sem`/`dbml2sql` version table now compares 14 Sep against 21 Sep on this machine instead of
against `install.md`.

VS Code was launched (`code .`, by the user). `%APPDATA%\Code\User\settings.json` came up with all
three keys already `true` — `chat.useClaudeMdFile`, `chat.useAgentsMdFile`,
`github.copilot.chat.codeGeneration.useInstructionFiles`. The user opened *Show Chat Debug View* and
found `REPLY_CEILING` inside the `copilot-instructions.md` attachment of an actual request payload —
both `AGENTS.md` and `~/.copilot/copilot-instructions.md` are loaded as separate attachments, content
current with this session's relink.
