---
machine: windows-ema-pf5n4xe7
platform: Windows 11
os_version: 10.0.26200
shell: PowerShell 7.6.5
python: 3.14.7
repo: C:\Users\voutsas\Work\Development\agentic-coding\agentic-workbench
verified: 2026-09-29
author: Achilleas Voutsas
version: 0.2.0
---

# Windows 11 — `EMA-PF5N4XE7`

State for this box only. Policy is in [`../agent/AGENT-INSTRUCTIONS.md`](../agent/AGENT-INSTRUCTIONS.md); install routes are
in [`../cli/<tool>/install.md`](../cli/). **Where a measured fact here contradicts either, the fact wins** — it
is the one that was measured.

## Paths

| What | Where |
|---|---|
| This repo | `C:\Users\voutsas\Work\Development\agentic-coding\agentic-workbench` |
| Home | `C:\Users\voutsas` |
| `pwsh` | `C:\Users\voutsas\scoop\apps\pwsh\current\pwsh.exe` |
| Package manager | `scoop` |

Not the `~/Development/agentic-coding/` path the macOS notes use.

## Shell

PowerShell 7.6.5, not bash.

- `$env:VAR = 'x'`, not `export`.
- **`>` and `Out-File` default to UTF-16LE and corrupt markdown.** Use `Set-Content -Encoding utf8`,
  or write from Python.
- There is no `sed`, `awk`, `tr` or `head`, so there is no shell route to an in-place substitution at
  all. That makes [`../agent/AGENT-INSTRUCTIONS.md`](../agent/AGENT-INSTRUCTIONS.md)'s *editing a file is an editor's job*
  the only route here, not a preference: use the editor tool. Where an edit is genuinely programmatic,
  it goes through this repo's present `.venv` like any other Python — see *Python scaffolding* below.

**The Bash tool cannot resolve anything on `PATH`.** It receives the Windows semicolon-separated
`PATH` and hands it to Git Bash, which expects colons, so every bare command fails
`command not found` — `ls` and `git` included. Call binaries by absolute POSIX path, and drive real
work through pwsh:

```
/c/Users/voutsas/scoop/apps/pwsh/current/pwsh.exe -NoProfile -Command '…'
```

### `PATH` differs between the agent and the user

Measured 2026-08-26. **The `PATH` an agent observes is not this machine's `PATH`**, so never report one
as the other:

| Source | Entries | Git-related entries |
|---|---|---|
| Registry — `Machine` + `User`, what a fresh shell gets | 45 | `scoop\apps\git\current\cmd` only |
| Runtime, in a `pwsh` launched from the Bash tool | 57 | `…\git\2.55.0.5\usr\bin` ×3 at positions 4/5/7, plus `mingw64\bin` and `usr\local\bin` — all **ahead of** `C:\WINDOWS\system32` at 13 |

The cause is that the Bash tool *is* Git Bash — `MSYSTEM=MINGW64` and
`SHELL=…\git\current\bin\bash.exe` — and it prepends its MSYS directories before `pwsh` inherits them.
The extra 12 entries are that injection plus scoop shims.

Check the scopes separately, and quote which one you read:

```powershell
$env:PATH -split ';'                                     # process scope
[Environment]::GetEnvironmentVariable('PATH','User')      # the GUI User table
[Environment]::GetEnvironmentVariable('PATH','Machine')   # the GUI System table
```

`Get-Command <name> -All` shows resolution order **for the calling process only**. It is not evidence
about what the user's terminal does.

### There is a PowerShell tool — ask before switching a folder to it

It replaces Git Bash as the shell tool, which is what removes the defect above. Measured 2026-09-02 on
`@anthropic-ai/claude-code` 2.1.258, by running the same headless prompt in two empty folders:

| Folder holds | `claude -p "Do you have a PowerShell tool…"` |
|---|---|
| nothing | `NO` |
| `.claude/settings.local.json` with `env.CLAUDE_CODE_USE_POWERSHELL_TOOL` = `"1"` | `YES:PowerShell` |

So the switch is **per project folder**, and the tool is named `PowerShell`. The flag is read at session
start: a file written mid-session changes nothing until a session is started in that folder again.

**Ask once per folder, and never create the file unasked.** The first time work in a folder needs the
shell:

1. Read `.claude/settings.local.json` there. If it already carries the flag, say nothing and carry on.
2. If it does not, **ask the user whether to create it, and wait.** A decline holds for the rest of the
   session — fall back to the absolute-path `pwsh` route above and do not ask twice.
3. On a yes, write exactly this, then tell them it takes a restart in that folder:

   ```json
   { "env": { "CLAUDE_CODE_USE_POWERSHELL_TOOL": "1" } }
   ```

4. If the file exists already, **merge into its `env` block** rather than replacing the file, and check
   the folder's `.gitignore` covers `.claude/settings.local.json` — it is machine-local, not shared.

Without a file at all, one line in the launching shell does the same thing for a single run — the shape
of the LibreOffice `PATH` switch under *docling* below:

```powershell
$env:CLAUDE_CODE_USE_POWERSHELL_TOOL = '1'; claude
```

**Two other files stay out of this.** `~/.claude/settings.json` may never be written by an agent, per
*`settings.json` is not drift* below. `~/.claude/settings.local.json` — the user-level layer — is kept
absent by design, per [`../agent/README.md`](../agent/README.md#deliberately-not-tracked): it was
created holding this flag on 2 September 2026 and removed the same day, because one file there puts
**every** session on a preview tool, including the folders the route above already serves.

Still a preview, and not yet exercised on real work here: **pending, not cleared.**

#### The flag belongs to this machine's live `settings.json`, not the shared repo copy

Verified 2026-09-03 by reading `~/.claude/settings.json` directly: `env.CLAUDE_CODE_USE_POWERSHELL_TOOL`
is `"1"`, added by hand to the live file. **It must not be added to
[`../agent/settings.json`](../agent/settings.json)** — that copy is shared unmodified with macOS, and
every reason for the flag above (Git Bash's MSYS `PATH` injection) is specific to this machine's shell,
not to the tool in general. Where this repo needs a record of the need, it belongs here, not there.

#### A `SessionStart` hook raises the question, so it does not depend on being remembered

Registered in `~/.claude/settings.json` on 2 September 2026 — the file that is merged by hand, so the
block is the user's edit, not an agent's. Verified afterwards: the `env` block came through intact and the
key list is now `env, permissions, model, enabledPlugins, fastMode, tui, theme, hooks`. No pre-merge
backup was taken, so the 26 August `~/.claude/settings.json.bak` is the only fallback on disk.

**The block belongs in the live file only.** It was pasted into
[`../agent/settings.json`](../agent/settings.json) as well, and reverted the same day: that copy is
shared with macOS, where this Windows absolute path would open every session with a failing hook.

```json
"hooks": { "SessionStart": [ { "hooks": [ { "type": "command",
  "command": "…\\pwsh.exe -NoProfile -File C:\\Users\\voutsas\\.claude\\hooks\\powershell-tool-prompt.ps1"
} ] } ] }
```

The script itself now has a tracked reference copy at
[`../agent/hooks/powershell-tool-prompt.ps1`](../agent/hooks/powershell-tool-prompt.ps1) — same
treatment as `settings.json`: the body is portable, the registration stays machine-local, copied by
hand into `~/.claude/hooks/powershell-tool-prompt.ps1`. It stays silent unless the folder needs the
question, logs every decision to `powershell-tool-prompt.log` beside itself, and always exits 0 so a
fault can never block a session. Measured 2026-09-02 by invoking it directly:

| Case | Result |
|---|---|
| folder without the flag | 794-char `additionalContext`, `hookEventName` = `SessionStart` |
| folder carrying the flag | silent |
| `cwd` read from the stdin payload, spawned as a child with stdin redirected | silent — reads the session's folder, not `$PWD` |
| internal failure | written to the log, exit 0 |

**Whether Claude Code actually calls it is unverified: pending.** `claude -p` fired it in no
configuration tried — fresh temp folder or this repo, via `--settings`, via a project
`.claude/settings.local.json`, and via the registered user-level block; `--debug` returned a single line
with nothing matching `hook`. `claude.exe` carries the string *"SessionStart hooks cancelled (control
stream closed)"*, which fits a single-shot print session, and no `managed-settings.json` or
`disableAllHooks` exists here to explain it otherwise. **The only test that settles it is an interactive
restart, and the evidence is a new line in that log.**

**Outstanding: a `PreToolUse` registration the tracked script expects but the live file doesn't have.**
The script's own header comment (`../agent/hooks/powershell-tool-prompt.ps1`) documents itself as
registered under both `hooks.SessionStart` and `hooks.PreToolUse` (matcher `"Bash"`), with the latter as
the backstop that fires right before the first Bash call. Verified 2026-09-03 by reading
`~/.claude/settings.json` directly: only `hooks.SessionStart` is present; there is no `PreToolUse` entry.
Needs adding to the live file, by hand, in the same shape as the `SessionStart` block above:

```json
"hooks": {
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "C:/Users/voutsas/scoop/apps/pwsh/current/pwsh.exe -NoProfile -File C:/Users/voutsas/.claude/hooks/powershell-tool-prompt.ps1"
        }
      ]
    }
  ]
}
```

Until this is added, the script's `PreToolUse` branch is dead code on this machine — only the
`SessionStart` path can ever fire.

If `~/.claude` is ever rebuilt, the script has to be recreated; whether it moves into the tracked tree is
an open call.

## Python scaffolding

Measured 2026-09-14 in this repo. [`../agent/AGENT-INSTRUCTIONS.md`](../agent/AGENT-INSTRUCTIONS.md) requires every Python
invocation to run through the project's venv, so this table is the gate on any `python` command here:

| Piece | State | Note |
|---|---|---|
| `.python-version` | present, tracked | `3.14` — so there is nothing to ask about |
| `pyproject.toml` | present, tracked | `requires-python = ">=3.12"`, `dependencies = []` |
| `.venv` | **present** | use `.venv\Scripts\python.exe` |
| `uv` | 0.11.25 | `…\scoop\apps\python314\current\Scripts\uv.exe` |
| Global interpreter | 3.14.7 | `…\scoop\apps\python314\current\python.exe` — **not to be used** |

The version is pinned and the environment is ready. Run project Python commands through
`.venv\Scripts\python.exe`; do not use the global interpreter.

### Fresh-clone install validated

Validated 2026-09-29 in
`C:\Users\voutsas\Work\Development\agentic-coding\junk\agentic-workbench-windows-validation`, a
fresh Windows clone using the tracked `3.14` pin and `uv.lock`. `uv sync` created `.venv` with
CPython 3.14.7 and installed the ten locked development packages, including Pyright, pytest, and
Ruff. The resulting persisted status report exited 0; its Pandoc row read `workstation tool for
fetch-to-markdown, pdf-deliverable`. The retained report is
`status-windows-ema-pf5n4xe7-voutsas-20260929T175322+0200.md` in that clone.

## Git

`core.autocrlf=true` and `core.symlinks=false`.

The repo carries a [`.gitattributes`](../../.gitattributes) pinning `eol=lf` on `pre-push` and `*.py`,
which fixes the `#!/usr/bin/env bash` *bad interpreter* failure — **for files checked out after it
landed.** This working tree predated it: `.gitattributes` was committed 25 August 2026 at 12:30, while
`pre-push` had been written at 18:20 the day before, so 11 files sat at `i/lf w/crlf` until they were
re-checked-out on 26 August.

**`git check-attr` cannot detect this** — it reported `eol: lf` on a file the working tree held as CRLF,
because the attribute governs writes and is never applied retroactively. Ask about the working tree:

```powershell
git ls-files --eol | Select-String "w/crlf" | Where-Object { $_ -match "eol=lf" }
```

Empty is correct. Anything listed is fixed by `Remove-Item <file>; git checkout -- <file>`, which loses
nothing because the index already holds LF.

Because `core.symlinks=false`, a symlink committed to this repo would check out here as a text file
containing its target path. Nothing in the repo relies on one.

### Git HTML help opens browser tabs in Copilot sessions

Measured 2026-09-29: Scoop Git's system configuration at
`C:\Users\voutsas\scoop\apps\git\2.55.0.5\etc\gitconfig` sets `help.format=html`. The reported
Copilot-session symptom is tabs such as `file:///C:/Users/voutsas/scoop/apps/git/2.55.0.5/mingw64/share/doc/git-doc/git-diff.html`;
this is Git's HTML rendering of `git diff --help`, not a diff failure.

Use `git diff -h` (and the equivalent `-h` form for other Git subcommands) in automated routes. The
tracked claim verifier does so. Do not set `help.format=man` here: the measured transient invocation
`git -c help.format=man help diff` exits 128 because this Git installation has no `man` viewer.
`core.pager` and `GIT_PAGER` do not control this behavior. The shared route is
[`../agent/setup/windows.md`](../agent/setup/windows.md#git-html-help-in-copilot-sessions).

### The Azure DevOps remote needs `credential.useHttpPath`

The remote is `origin`, `https://euemadev@dev.azure.com/euemadev/EA/_git/agentic-workbench`. Without
that setting, every fetch and push prints `fatal: Cannot determine the organization name for this
'dev.azure.com' remote URL` — **after** the transfer, so a push that printed it had already succeeded,
which is what makes it easy to misread as a failure. Having the org as the URL's user, which this remote
already does, is not enough for the credential helper. Set once, by the user, on 21 September 2026:

```powershell
git config credential.useHttpPath true
```

`git fetch` and `git ls-remote origin refs/heads/main` then both run silent, exit 0. This is local
config, not repo config — a fresh clone here needs it again.

## Claude Code config — installed

**23 of 23 linked**, re-checked 6 October 2026 by
`python workstation\scripts\link_config.py --agent claude --agent copilot`, exit 0 — up from 21 of 21
as the `SKILLS` tuple grew to add `session-signature`.

| Artefact | Kind | Status |
|---|---|---|
| `skills/review`, `skills/python-quality`, `skills/verify-docs`, `skills/fix-findings`, `skills/pdf-deliverable`, `skills/fetch-to-markdown`, `skills/confluence-publish`, `skills/confluence-export`, `skills/setup-mcp-servers`, `skills/session-signature` | dir | linked |
| `copilot/skills/review`, `copilot/skills/python-quality`, `copilot/skills/verify-docs`, `copilot/skills/fix-findings`, `copilot/skills/pdf-deliverable`, `copilot/skills/fetch-to-markdown`, `copilot/skills/confluence-publish`, `copilot/skills/confluence-export`, `copilot/skills/setup-mcp-servers`, `copilot/skills/session-signature` | dir | linked |
| `CLAUDE.md` | file | linked |
| `copilot/copilot-instructions.md` | file | linked |
| `machine.md` | file | linked |
| `settings.json` | — | excluded by design; merged by hand — see below |

**23 of 23 linked.** `settings.json` is excluded by design — it is merged by hand.

Re-check with the same command. Do not edit this table by hand. `Kind` says what the source is, not how
it is linked — `dir` if the source is a directory, else `file` (`link_config.py`, the `kind =` line in
its report); on Windows a `dir` is still a junction and a `file` a hardlink, per the module's
link-creation docstring.

**The original link, 21 September 2026:** `python workstation\scripts\link_config.py --agent claude
--agent copilot --apply --force`, exit 0, reporting 15 of 15 (the `SKILLS` tuple then had six entries).
`--force` was needed: `CLAUDE.md`, `machine.md` and `copilot/copilot-instructions.md` all read
`diverged` first — triaged by diffing each against its repo source before forcing, per *the three
hardlinks sever constantly* below; all three carried only stale text the repo had since superseded,
nothing live-only, so the overwrite was safe.

### The plugin route is also installed and verified, 5 October 2026

A second, independent route to the same nine `SKILLS` tuple skills: `workstation/agent/` is now a
plugin root for both tools (`workstation/agent/README.md` § *Install the skills as a plugin
instead*). Verified live on this machine, not just file-shape:

```powershell
claude plugin marketplace add ./workstation/agent
claude plugin install workbench-skills@agentic-workbench
copilot plugin marketplace add ./workstation/agent
copilot plugin install workbench-skills@agentic-workbench
```

Both succeeded. `claude plugin details workbench-skills` reported all 9 skills (`confluence-export`,
`confluence-publish`, `fetch-to-markdown`, `fix-findings`, `pdf-deliverable`, `python-quality`,
`review`, `setup-mcp-servers`, `verify-docs`), enabled, v0.1.0. `copilot plugin list` reported the
same, noting it is "loaded live from `…\workstation\agent`, so edits take effect on the next
session — nothing was copied." Both installs are **kept** on this machine, by choice, alongside the
`link_config.py` route above rather than replacing it. One real bug surfaced in the process: both
`marketplace.json` files were missing the required `owner` field — both tools refused to add the
marketplace until it was added (fixed in `7852ced`).

### Copilot MCP servers validated end to end on 29 September 2026

Copilot CLI reloaded four MCP servers. `ado-remote-mcp` successfully listed **165** accessible private
Azure DevOps projects in `euemadev` without another Entra sign-in. `open_drawio_mermaid` successfully
created the `Start -> Validate -> Complete` diagram and returned a Draw.io Editor URL. The project
names and generated URL are intentionally not recorded here. Both servers' registration status,
per [`../mcp/README.md`](../mcp/README.md) and their own `setup.md` files, is this machine's state, not
a route fact — recorded here rather than there.

**Databricks managed MCP services — catalog snapshot, 29 September 2026.** The live `system.ai`
catalog on this workspace contained eight services, of which only `genie_one_mcp` was internal (the
rest are connection-backed SaaS services the registration script excludes) — see
[`../mcp/databricks-mcp/setup.md`](../mcp/databricks-mcp/setup.md#the-server-family). Not a portable service
list; a different workspace or profile can differ.

### d2's own SVG rasterises through `magick` without `rsvg-convert`

Measured 29 September 2026: `d2 --scale 2` on the one-line source `a -> b` compiled to SVG at exit 0,
then `magick <that svg> out.png` (no `rsvg-convert` on `PATH` at all — `Get-Command rsvg-convert`
returns nothing here) converted it directly at exit 0 to a 510×868 PNG with 142 distinct colours —
antialiased text, not a blank canvas — despite an Inkscape font-face warning on stderr. Confirms, with
an actual d2 diagram rather than a plain-text SVG, what
[`../cli/magick/quick_start.md`](../cli/magick/quick_start.md) § *SVG input* already measured on this
scoop ImageMagick build: the `rsvg-convert` hop that brew's macOS build needs is not needed here. See
[`../cli/d2-cli/quick_start.md`](../cli/d2-cli/quick_start.md) for the reconciled rule.

**The first `--force`, on 26 August 2026**, was the same situation with more at stake: `CLAUDE.md` read
`diverged` because the live copy was a plain edited file, not a link. That was safe only because the
drift had already been triaged: of its 14 live-only lines, 12 were
superseded by expanded versions in the repo copy, and the remaining two were macOS facts rescued into
[`macos-workstation.md`](macos-workstation.md) first. The pre-`--force` file was kept as
`~/.claude/CLAUDE.md.bak`. **Do not reach for `--force` without doing that triage** — the script compares
bytes and cannot know whether it happened.

### The three hardlinks sever constantly — assume they are broken

Only the file links are at risk — `CLAUDE.md`, `machine.md` and `copilot/copilot-instructions.md`; the
eighteen skill junctions (nine skills × two agents, as of 29 September 2026) survive everything. **Two
causes, and the second fires on ordinary work:**

**Git operations.** These links were made while the repo sat on `workstation-multi-machine`. Git replaces
a tracked file rather than writing through it, so merging to `main`, switching branches, or pulling a
change to `agent/AGENT-INSTRUCTIONS.md` detaches both — silently, frozen at the old content.

**Any atomic-saving writer, including Claude Code's own `Edit` tool.** Observed 26 August 2026: editing
this file through the repo path severed `machine.md` within minutes of linking it. An atomic save writes
a temporary file and renames it over the target, which creates a new inode, so the live copy stops
tracking the repo while still looking fine. The report read `diverged`, and `~/.claude/machine.md` was
still serving the pre-edit text to any session that read it.

**So: any edit to `agent/AGENT-INSTRUCTIONS.md` or this file is followed by a re-link, not just a commit.**

```powershell
python workstation\scripts\link_config.py --apply
```

Plain `--apply` repairs a `detached` link — one whose content still matches. It reports `diverged` and
refuses when the two have drifted, which is the case above: the severed copy held the old text while the
repo held the new. There, confirm the stale side carries nothing unique — `Compare-Object` showed 44
lines only in the severed copy, all of them text the edit had replaced — and then use `--force`.

### The `pre-push` gate uses the tracked shim — verified 29 September 2026

The Windows shim replaced the stale copied hook and ran end to end on a real push:

```powershell
Copy-Item workstation\agent\skills\review\scripts\pre-push.windows .git\hooks\pre-push -Force
git ls-files --eol workstation/agent/skills/review/scripts/pre-push workstation/agent/skills/review/scripts/pre-push.windows
git push --set-upstream origin av-20260929-junk
```

Both hook files report `i/lf w/lf attr/text eol=lf`. The push printed
`pre-push: ruff check and ruff format --check`, passed `repo_check.py`, Ruff, and every configured unit
test suite, then Azure DevOps accepted the new branch. The shim executes the tracked
[`../agent/skills/review/scripts/pre-push`](../agent/skills/review/scripts/pre-push), so future pulls
automatically use its current implementation.

It must be a **plain copy**, not a link — git will not run a hook through a junction. The 26 August check
found the copy executing via its own shebang with 0 CR bytes.

### `settings.json` is not drift

The live file carries an `env` block — `CLAUDE_CODE_USE_BEDROCK`, `AWS_REGION`, `AWS_PROFILE` and
Bedrock-prefixed model IDs — that this repo deliberately does not. **Claude Code must run against
Bedrock on this machine for compliance reasons**, so that block stays where it is:

- **Never link, overwrite or regenerate `~/.claude/settings.json`**, and do not move the `env` block to
  `settings.local.json`. [`../agent/setup/windows.md`](../agent/setup/windows.md) omits the file from
  its link block for this reason.
- Shared keys are merged into it **by hand**, by the user. **The four top-level keys were merged on 26
  August 2026** and the delta now prints `in sync`; a backup remains at `~/.claude/settings.json.bak`
  and the live file was **not** written by any agent. One row is still outstanding:

| Key | Value wanted | Where it goes | Live now — measured 2026-08-26 | State |
|---|---|---|---|---|
| `permissions` | `{"defaultMode": "auto"}` | top level | matches | merged |
| `enabledPlugins` | `{"pyright-lsp@claude-plugins-official": true}` | top level | matches | merged |
| `tui` | `"fullscreen"` | top level | matches | merged |
| `fastMode` | `true` | top level | matches | merged |
| `env.ANTHROPIC_MODEL` | `eu.anthropic.claude-opus-5` | inside `env` | `eu.anthropic.claude-sonnet-5` | **outstanding** |
| `hooks` | `PostToolUse` block from [`../agent/settings.json`](../agent/settings.json); `SessionStart` is **not** from that file — it was added straight to the live file, per *A `SessionStart` hook raises the question* above | top level | present, measured 21 September 2026: `SessionStart` runs `powershell-tool-prompt.ps1`; `PostToolUse` (matcher `Edit\|Write`) tries `.venv/bin/python` then `.venv/Scripts/python.exe` before `ruff_on_edit.py`, `exit 0` if neither exists | merged |

`env` survived the merge intact — all five members present, `CLAUDE_CODE_USE_BEDROCK=1`,
`ANTHROPIC_SMALL_FAST_MODEL=eu.anthropic.claude-haiku-4-5` (the **legacy** key —
`ANTHROPIC_DEFAULT_HAIKU_MODEL` replaces it, per
[`../agent/README.md`](../agent/README.md#the-merge-procedure)) — which was the thing at risk. Top-level
`model: "opus"` already matches and is the setting a session actually resolves to;
`env.ANTHROPIC_MODEL` is the Bedrock ID passed through to the provider. They are independent, so the
last row is the only edit `env` needs.

**`in sync` alone does not clear that last row, and this is how it was found.** The delta compares only
the keys the repo copy has, and the repo copy has no `env` block, so it printed `in sync` on 26 August
while `ANTHROPIC_MODEL` was still `sonnet-5`. The `env` model IDs have to be read separately — step 6 of
the procedure in [`../agent/README.md`](../agent/README.md#the-merge-procedure) now runs both checks
for that reason.

## CLI toolchain

Probed on `EMA-PF5N4XE7` (Windows 10.0.26200, Python 3.14.8) by
[`../scripts/inventory.py`](../scripts/inventory.py) on 6 October 2026.

**17 of 17 usable.** This probe ran from the repo's `.venv`, on the 3.14 pin; its Python version
identifies the probe, not the machine's default Python. The 3.12.10 the 29 September probe recorded
matched no environment recorded here; this probe supersedes it.

| Command | Product | Status | Version | Detail |
|---|---|---|---|---|
| `confluence-sync-md`, `md2conf` | confluence-sync-md | installed | 0.6.0 | — |
| `d2` | D2 (Terrastruct) | installed | 0.9.0 | — |
| `databricks` | Databricks CLI | installed | 1.19.0 | — |
| `dbml2sql`, `sql2dbml`, `db2dbml` | DBML CLI | installed | 9.0.0 | — |
| `defuddle` | Defuddle | installed | 0.19.4 | — |
| `docling` | Docling | installed | 2.131.0 | — |
| `jq` | jq | installed | 1.8.2 | — |
| `magick` | ImageMagick | installed | 7.1.2-32 | — |
| `mmdc` | Mermaid CLI | installed | 11.16.0 | — |
| `pandoc` | Pandoc | installed | 3.12 | — |
| `plantuml` | PlantUML | installed | 1.2026.8 | — |
| `playwright` | Playwright | installed | 1.63.0 | — |
| `sem` | Sem (Ataraxy Labs) | installed | 0.13.0 | — |
| `tesseract` | Tesseract OCR | installed | 5.5.3.20260724 | — |
| `typst` | Typst | installed | 0.15.1 | — |
| `ug`, `ucode` | Unity Gateway (Databricks) | installed | 0.2.0+36.gafd2ce1 | — |
| `weasyprint` | WeasyPrint | installed | 70.0 | — |

Regenerate with `python workstation/scripts/inventory.py`. Do not edit the table by hand.

### `docling` was quarantined and is now cleared

Blocked 24–25 August 2026 as an EDR/antivirus quarantine: `docling.exe` could not even be **read**,
while the identical 46,080-byte `playwright.exe` shim beside it read fine and the ACL granted
`EMEA\voutsas Allow FullControl`. Resolved by the user on 26 August 2026. Verified the same day, by the
same readability test that diagnosed it:

| Check | Result |
|---|---|
| `[IO.File]::ReadAllBytes(…\.local\bin\docling.exe)` | reads — 46,080 bytes |
| Same call on `docling-tools.exe` | reads — 46,080 bytes |
| `docling --version` | `Docling version: 2.122.0`, on `cpython-312 (3.12.10)` |
| `docling convert --to md` on a 132 KB `.docx` | converted in 3.45 s |

The original pipx route ran it from `C:\Users\voutsas\AppData\Local\pipx\pipx\venvs`, not the
`~\.local\pipx\venvs` path the original diagnosis probed. The current route is `uv tool` (Docling
2.131.0 in the 29 September inventory); `pipx list` is empty. **Ingestion of PDF and Office formats is
no longer blocked here.** The general form of the readability test stays in
[`../cli/docling/install.md`](../cli/docling/install.md) — it is the discriminator that separates this
from the `whoami` case below.

#### Images need LibreOffice on `PATH`, and it is deliberately not there

LibreOffice **26.2.5 is installed** at `~\scoop\apps\libreoffice\current\LibreOffice\program`, but scoop
created **no shim**, so `soffice` is on neither `PATH` scope and docling drops every image by default.
That is the intended state, not an oversight — measured 26 August 2026 on the 132 KB
`Enterprise architecture principles.docx`:

| `soffice` resolvable | Convert time | Output | Images |
|---|---|---|---|
| no — the default here | 3.45 s | 25,646 bytes | 0 |
| yes — `PATH` prepended for one shell | **356.62 s** | 367,658 bytes | **14** |

100× slower, so a permanent shim would tax every conversion for a feature most do not need. **Turn it on
for the run that needs it:**

```powershell
$env:PATH = "$HOME\scoop\apps\libreoffice\current\LibreOffice\program;" + $env:PATH
```

The 367,658-byte result matches the 366,040-byte reference copy of the same document measured when
this was recorded — 14 images, 18 headings both. Without it, headings
and table rows still match exactly, so **a size drop of that scale is missing images, not a failed
conversion.** Check the image count, never the exit code.

`DOCLING_LIBREOFFICE_CMD` is inert despite docling's own warning naming it; the evidence and the `.com`
vs `.exe` trap are in
[`../cli/docling/install.md`](../cli/docling/install.md#embedded-images-need-libreoffice).

If a permanent shim is ever wanted, the command is the user's to run — and note it uses `.com`:

```powershell
scoop shim add soffice "$HOME\scoop\apps\libreoffice\current\LibreOffice\program\soffice.com"
```

### `whoami` and `hostname` are blocked in git's `usr/bin`, and it does not matter

Measured 2026-08-25. Not the `docling` case, and **not worth an IT request**:

| Check | Result |
|---|---|
| `C:\WINDOWS\system32\whoami.exe` | runs — `emea\voutsas` |
| `…\scoop\apps\git\2.55.0.5\usr\bin\whoami.exe` | **Access is denied** on launch |
| Same file, `[IO.File]::ReadAllBytes` | **reads fine**, 33,887 bytes |
| Same file, `(Get-Acl …).Access` | `EMEA\voutsas Allow FullControl` |
| Siblings `basename`, `sed`, `grep`, `id` | all run |
| Sibling `hostname.exe` | also denied |

Readable file, permissive ACL, working siblings, two specific names refused: that is a process-creation
rule, not a quarantine. `whoami` and `hostname` are standard reconnaissance commands, and a copy of one
running from a user-writable directory is a much stronger signal than the System32 original — which is
why System32's copies work and these do not.

**Consequence: none, and none for the user's own shell at all.** Git's `usr\bin` is *not* on this
machine's `PATH` — neither scope carries it, and resolving `whoami` against the registry-built `PATH`
gives `C:\WINDOWS\system32\whoami.exe`. The blocked copies are reachable only from the agent's shell,
for the reason in *`PATH` differs between the agent and the user* above. Use `$env:USERNAME` and
`$env:COMPUTERNAME`, or call System32 by absolute path.

### Two installs are behind their recorded version

Found by the 14 September probe, left alone deliberately —
[the version-currency rule](../cli/README.md#version-currency--raise-it-dont-fix-it) says raise it,
don't fix it, because an upgrade can change output format part-way through a piece of work. The 21
September probe shows no change on this machine since then:

| Command | Installed here (14 Sep) | Installed here (21 Sep) | Route to upgrade |
|---|---|---|---|
| `sem` | 0.13.0 | 0.13.0 — unchanged | see [`../cli/sem-cli/install.md`](../cli/sem-cli/install.md) |
| `dbml2sql` | 9.0.0 | 9.0.0 — unchanged | `npm install -g @dbml/cli@latest` |

These are the user's call. Nothing here is a hold, so nothing is recorded as one.

## Validation (`../validation/windows.md`)

Run 21 September 2026. Sections A and B are the relink and inventory probe above. C–E:

**C. Document conversion.** `docling convert` on both fixtures matched the macOS-documented result
exactly: `chartex.docx` gave 2 base64 images, 4 `Image not available` placeholders, and its chart data
as pipe tables; `shapes-with-text.docx` gave all five shapes' text. Byte-identity with macOS's output
is still unchecked — no macOS copy was diffed against.

**D. The JS-hydrated route.** The raw fetch (`curl` + `defuddle`) measured 206 words on
`retirejs.github.io/retire.js/` — "low hundreds," as expected. The rendered half was blocked when this
section first ran and is now closed: see *Playwright's browser binaries are now installed* below. The other open question — whether
`render_page.py`'s exit-2 message names the right interpreter — is settled, and it uncovered a real bug:
the `python=` part is correct (`sys.executable`, dynamic), but the suggested fix-it command was
hardcoded POSIX (`/playwright/bin/python`) and would have failed if pasted verbatim on Windows. Fixed in
[`../agent/skills/fetch-to-markdown/scripts/render_page.py`](../agent/skills/fetch-to-markdown/scripts/render_page.py):
the command now reads `Scripts/python.exe` when `os.name == "nt"`. Re-verified: the message now prints
`.../playwright/Scripts/python.exe`. The fetch-to-markdown suite (78 tests) still passes.

**E. The repo's own gates.** `repo_check.py`: all enabled checks passed. Every `.pre-push-tests` suite
passed — **all seven of them**: 149, 34, 78, 19, 134, 160 and 17 tests, 591 in total. The 160 is
`verify-docs/tests`, which stood at 141 before this session's nineteen new tests for the two flag gaps,
the exemption notice and the evidence wording. The largest,
`workstation/scripts/tests`, was omitted from the first record of this run and is the one holding
`test_readme_skills.py`, `test_python_version.py` and `test_link_config.py`. The 134 is
`review/tests`, which stood at 106 before this session's `register` check added 28. The last, 17, is
`workstation/agent/hooks/tests`, expanded this session by the `apply_patch` fix in `dae4ab4`. `ruff check .` and
`ruff format --check .` both clean across the repo (98 files).

`verify_claims.py --repo .` (offline tier) exited 1 on every run of this section until the last. First
run: 661 verified, 609 unverifiable, 6 refuted. After this session's document fixes and four path globs in
`.verify-claims-allow`: 3 refuted. After the two checker fixes below: **0 refuted, exit 0**, against
roughly 1,320 claims extracted — the verified and unverifiable totals shift with every markdown edit, so
only the refuted count is worth recording. Every refuted row, on every run, was a verifier false positive
rather than a doc bug, and they were *not* harmless: the pre-push hook scopes this script to the markdown
in the push, so a push touching one of those files was refused until the row cleared.

| Refuted claim | Why it is not a doc bug | Cleared? |
|---|---|---|
| the POSIX and Windows venv interpreter paths (×2) | each line already names the other layout in the same sentence; a venv has one or the other, so one of the pair cannot exist on any given machine | yes — four globs in `.verify-claims-allow`, which is what that file is for |
| VS Code's workspace settings path (`agent/setup/README.md:178`, and this file quoting it) | a scope table row saying where VS Code *can* put workspace settings in whichever repo you open, not a claim that this repo has one | yes — same route |
| the `--porcelain` flag, on `git status` (×1, `AGENT-INSTRUCTIONS.md:86`) | probed here: it **is** in that command's `-h` output, written `--[no-]porcelain[=<version>]`, so a plain substring search for the flag misses it | yes — the verifier now matches that bracket form on every rung of the help ladder |
| the `--staged` flag, on `git diff` (×2, `AGENT-INSTRUCTIONS.md:87` and `review/SKILL.md:134`) | probed here: genuinely absent from `-h`, which documents only the synonym `--cached`; the flag itself works and exits 0 | yes — one entry in the new `.verify-flags-allow`, which exempts a flag that works but that no help text prints |

`repo_check.py --corpus`, the new ingestion ledger, reported **0 of 76 entries ingested** on this machine
with `docs/landing-zone/` absent entirely — expected on a clone, since the corpus is gitignored, but
unrecorded until now. One entry was then ingested end to end to prove the route runs here: `SOLID
Relevance`, server-rendered route, all four quality checks passed, ledger now **1 of 76**. The other 75
are [`../../TODO.md`](../../TODO.md) item 20.

Both remaining rows needed a change to `verify_claims.py` rather than to any document, and got one in this
session: bracket-form matching for the first, and a repo-local flag-exemption file for the synonym. The
gate is green here — `6572b7b`, which closed the `TODO.md` item, carries the detail and the
eleven unit tests.

Two docling claims in this file's own docling section looked like a third, worse gap: they returned
**different verdicts depending on whether the run was scoped to one file or covered the repo**. They were
not a verifier defect. The probe timeout was 20 seconds while `docling` takes 17s to answer `--version`
and 20s to answer `--help` here, so the verdict turned on machine load — now 120s — and this file
omitted the conversion subcommand from an output-format invocation, which the verifier was right to
refuse.
Both fixed; the scoped run over this file now reports **0 refuted**.

## Not yet installed

Deliberate gaps, so they are not rediscovered as faults:

- **LibreOffice is installed but deliberately off `PATH`** — see the docling section above. Not a gap.

Resolved 26 August 2026 and no longer gaps: `~/.claude/machine.md`, the six skills for both agents, and
the `pre-push` hook are all in place per *Claude Code config* above; `docling` is unblocked. **Resolved
by 21 September 2026 and no longer gaps:** `defuddle`, `tesseract` and `weasyprint` — all three read
`absent` on 14 September and `installed` on 21 September; no route was recorded here, so how each was
installed is unknown. **Resolved the same day:** Playwright's Chromium browser binary, per below.
**Resolved by 29 September 2026:** `typst` — read `absent`/not on `PATH` on the 21 September probe,
`installed` at 0.15.1 in the CLI toolchain table above; no route was recorded here either.

### VS Code — launched, and it loads the global instructions

`code.cmd` resolves (`~\scoop\apps\vscode\current\bin\code.cmd`). Launched 21 September 2026 by the
user (`code .`), which created `%APPDATA%\Code\User\settings.json` holding all three keys `true`:
`chat.useClaudeMdFile`, `chat.useAgentsMdFile`, `github.copilot.chat.codeGeneration.useInstructionFiles`
— confirmed by reading the file directly. Confirmed loaded, not just configured: *Show Chat Debug View*
on a real request showed `AGENTS.md` and `~/.copilot/copilot-instructions.md` as two separate attachments,
and `REPLY_CEILING` — a string that exists only in those instruction files — inside the
`copilot-instructions.md` one.

### Playwright's browser binaries are now installed

Checked 21 September 2026, running `render_page.py` (the JS-hydrated fetch route) through the pipx
venv's interpreter: `BrowserType.launch` failed — `chrome-headless-shell.exe` was missing from
`~\AppData\Local\ms-playwright\`. The pip package was installed; the browser binaries were not. Fixed
the same day, by the user:

```powershell
& "C:\Users\voutsas\AppData\Local\pipx\pipx\venvs\playwright\Scripts\python.exe" -m playwright install chromium
```

Re-verified end to end afterward: `render_page.py` on `retirejs.github.io/retire.js/` wrote 224 KB of
rendered HTML; `defuddle parse --md --frontmatter` on it gave a 15,137-word body (`word_count: 17260` in
its own frontmatter count) against the 206-word raw fetch, with `title: "Retire.js"` — the real page
title. Validation section D is now fully closed, not just the raw half.

On 29 September, the `uv tool` Playwright route was also exercised after a temporary shim
*Access is denied* fault: `playwright --version` reported 1.63.0, Chromium installed, and
`$(uv tool dir)\playwright\Scripts\python.exe` ran `render_page.py https://example.com rendered.html`.
`Test-Path rendered.html` returned `True`. The cause or endpoint-security action that restored shim
execution was not observed.

**Still outstanding, and the user's to do:** one key — `env.ANTHROPIC_MODEL`, per *`settings.json` is not
drift* above. The four top-level keys are merged. Plus one interactive restart, to prove the
`SessionStart` hook fires — see *There is a PowerShell tool* above.
