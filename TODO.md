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

### 5. The Copilot and project links are unproven on Windows

Opened 2026-09-13. `--agent copilot`, `--project` and `detect.py` were measured on macOS only.

| Unproven | Why it could differ |
|---|---|
| `--project` creates a junction per repo skill in `.claude\skills` | the macOS run made symlinks; the junction branch of `make_link` has only run for `~/.claude` |
| `--agent copilot` lands in `$HOME\.copilot\skills` and `copilot` loads it | the setup README marks Copilot CLI paths on Windows **not measured** |
| `detect.py` finds VS Code through `APPDATA` and probes `code` | on Windows `code` resolves to a `.cmd` shim, which the version probe runs directly |

**Closes when:** [`workstation/validation/windows.md`](workstation/validation/windows.md) sections
A–E have been run on that machine — they carry these checks and the rest of the sitting — with the
results recorded in `workstation/machines/windows-ema-pf5n4xe7.md`. That file was written from the
macOS steps and has never run, so correct it from the run rather than trusting it; its two *Unknown on
Windows* notes are the parts most likely to be wrong.

### 9. The Azure DevOps pipeline has never run

Opened 2026-09-14: the only pipeline was `.github/workflows/verify-docs.yml`, which never runs for this
clone's only remote, `emaea`, an Azure DevOps repo. **Written 2026-09-19** as
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

### 16. VS Code has never been launched on the Windows machine

Opened 2026-09-18, narrowed 2026-09-21. `windows-ema-pf5n4xe7.md` was rewritten this session from a
live `link_config.py --agent claude --agent copilot --apply --force` (15 of 15 linked — three files
were `diverged`, triaged by diff, then forced) and `inventory.py --host ema-pf5n4xe7` (12 of 13 usable;
`defuddle`, `tesseract`, `weasyprint` cleared since 14 September, `typst` now probed and absent). The
settings table gained the `hooks` row, read from the live `~/.claude/settings.json`, and the
`sem`/`dbml2sql` version table now compares 14 Sep against 21 Sep on this machine instead of against
`install.md`.

Left open: `%APPDATA%\Code` does not exist on this machine at all — `code.cmd` resolves but VS Code has
never been run, so `chat.useClaudeMdFile`, `chat.useAgentsMdFile` and
`github.copilot.chat.codeGeneration.useInstructionFiles` cannot be set yet.

**Closes when:** VS Code is launched once on this machine (by the user), the three keys are set `true`
in `%APPDATA%\Code\User\settings.json`, and `REPLY_CEILING` is found in a *Show Chat Debug View* prompt.

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
