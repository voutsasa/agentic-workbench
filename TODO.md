---
role: Open work carried between sessions — committed new work and unproven existing gaps
updated: 2026-09-27
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

### 28. confluence-sync-md has no `reference.md`, and its global skills haven't run outside the demo

Opened 2026-09-27. `SOURCES.md` registers confluence-sync-md at its Azure DevOps URL, but the README
needs sign-in over plain HTTP (`curl` → `302`), and Azure DevOps addresses files as `?path=/docs/x.md`.
`clean_publisher_md.py` resolves relative links with `urljoin`, which can't produce that form, so a
conversion would carry dead links. The `confluence-publish` and `confluence-export` skills now run
`uv run --no-sync -- confluence-sync-md`, which reached the global 0.6.0 from this repo and the pinned
0.6.0 from `confluence-sync-md-demo`, but no publish or export has run through them since they moved
here.

**Closes when:** `workstation/cli/confluence-sync-md/reference.md` exists with its relative links in
Azure DevOps' `?path=` form; and, in a repository with no pinned copy, one `publish check` and one
`export preview` have run through the skills against a real target page.

### 27. The `uv tool` routes and `winget` for databricks-cli have not run on Windows

Opened 2026-09-27. Global Python CLIs moved from pipx to `uv tool install --python 3.12`. On macOS,
docling, playwright and unity-gateway were migrated and each passed a real-use check. On
`ema-pf5n4xe7`, docling, playwright and unity-gateway are still on pipx or absent, and
`winget install Databricks.DatabricksCLI` hasn't run. confluence-sync-md (`uv tool`, Python 3.14) hasn't
been installed there either. The pipx shim quarantine recorded in
`workstation/cli/docling/install.md` has not been tested against uv tool shims.

**Closes when:** on `ema-pf5n4xe7`, the pipx copies are uninstalled, the five Windows rows have run,
`inventory.py` reports all five tools `installed`, `render_page.py` runs under
`$(uv tool dir)\playwright\Scripts\python.exe`, and the result is recorded in that machine's note,
including whether EDR touched the uv shims.

### 25. The README *Install* steps have not run on Windows

Opened 2026-09-22. `README.md` § *Install* gained `uv sync`, the pre-push gate and `status.py` as steps
1–3; on macOS they ran end to end on a fresh clone (`uv sync` installed `pytest` and `ruff`, `status.py`
reported `READY`). Step 2 on Windows is item 24.

**Closes when:** on `ema-pf5n4xe7`, a fresh clone runs `uv sync`, then
`python workstation\scripts\status.py` exits 0 with a Requirement cell reading `workstation tool for
fetch-to-markdown, pdf-deliverable` on the Pandoc row — recorded in the machine note.

### 24. The Windows pre-push shim has not run on Windows

Opened 2026-09-21. `workstation/agent/skills/review/scripts/pre-push.windows` replaces the copied hook on
Windows; its 4 tests pass on macOS, and on macOS it runs the real hook end to end. `ema-pf5n4xe7` still has
the old copy of the hook itself.

**Closes when:** on `ema-pf5n4xe7`, `Copy-Item workstation\agent\skills\review\scripts\pre-push.windows
.git\hooks\pre-push -Force` has run, `git ls-files --eol` shows `w/lf` for both files, and a `git push`
prints the hook's `pre-push: ruff check and ruff format --check` line — recorded in the machine note.

### 20. The corpus on this machine is 93 of 94 entries

Opened 2026-09-21 at **0 of 76**, with `docs/landing-zone/` absent. On 2026-09-27
`repo_check.py --corpus` reports **93 of 94**, after `ado-remote-mcp` was ingested through the
server-rendered route (`div.content`, the page's second one; markup-noise 0, no relative links). The
one missing entry is `confluence-sync-md`, blocked on the Azure DevOps sign-in in item 28.

**Closes when:** `repo_check.py --corpus` reports 94 of 94.

### 9. The Azure DevOps pipeline has never run

Opened 2026-09-14: the only pipeline was `.github/workflows/verify-docs.yml`, which never runs for this
repo's only remote, `https://euemadev@dev.azure.com/euemadev/EA/_git/agentic-workbench`, an
Azure DevOps repo. The remote's *name* differs per clone — see each machine note. **Written 2026-09-19** as
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
into this file's item 17 and one closed in `d419f95`. Approve-each (step 2) did not run: the user answered the review's
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
