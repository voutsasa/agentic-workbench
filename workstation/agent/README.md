# Agent config

Hand-authored Claude Code config, versioned here and linked into `~/.claude/` so it is not scattered
through a home directory.

**Everything in this directory is shared by every machine, unmodified.** That is the invariant the rest
of the tree is arranged around, and it has three consequences:

- Anything about the *state* of a machine — paths, shell quirks, which tools run, what is broken —
  belongs in [`../machines/`](../machines/), not in `CLAUDE.md`. See
  [`../machines/README.md`](../machines/README.md) for the test.
- **`settings.json` here is a reference, not a link target** — the one file in this directory merged
  key-by-key rather than linked. See *Settings are merged, never linked* below.
- Anything else machine-local, and not provider-bound, belongs in `~/.claude/settings.local.json`,
  which is untracked by design.

Two authoring rules for `AGENT-INSTRUCTIONS.md`, kept here because they govern its edits, not a session:

- **Nothing machine-specific goes in it.** A shell quirk, an absolute path, a version number or a tool
  inventory written there is a defect; its *This machine* section points at `~/.agentic-workbench/machine.md`
  instead.
- **`MAX_REPLY_CEILING`'s number is written once**, in its *How to answer me* bullet. Skills refer to it by
  name, so change the number there alone.

## Contents

| Path | Goes to | How |
|---|---|---|
| `AGENT-INSTRUCTIONS.md` | `~/.claude/CLAUDE.md` | linked for Claude Code and VS Code with `chat.useClaudeMdFile` |
| `AGENT-INSTRUCTIONS.md` | `~/.copilot/copilot-instructions.md` | linked for Copilot CLI |
| `AGENT-INSTRUCTIONS.md` | `~/.agentic-workbench/AGENTS.md` | linked for every agent — the one assistant-neutral home copy, named like this repo's own root `AGENTS.md` rather than any assistant, for an integration that has no agent-specific route of its own yet |
| `settings.json` | `~/.claude/settings.json` | **merged by hand — never linked** |
| `skills/<skill>/` | `~/.claude/skills/<skill>` | linked — one per name in [`../scripts/link_config.py`](../scripts/link_config.py)'s `SKILLS` tuple |
| `../machines/<platform>-<id>.md` | `~/.agentic-workbench/machine.md` | linked for every agent — the instructions name this one path, under the workbench's own home rather than any assistant's |
| `hooks/powershell-tool-prompt.ps1` | `~/.claude/hooks/powershell-tool-prompt.ps1` | **reference copy — copied by hand, never linked** |
| `hooks/ruff_on_edit.py` | `~/.claude/hooks/` and `~/.copilot/hooks/` | linked with `link_config.py --hooks` |
| `hooks/ruff-on-edit.copilot.json` | `~/.copilot/hooks/ruff-on-edit.json` | linked with `link_config.py --hooks --agent copilot` |

The `../machines/<platform>-<id>.md` row above is the indirection that keeps this directory
platform-neutral: one fixed path, different content per machine, so `CLAUDE.md` can point at machine
truth without naming a platform. `~/.agentic-workbench/AGENTS.md` is the same indirection applied to
the *instructions themselves*, not just machine state.

"Linked" for every **file** row above is a symlink on macOS; on Windows it is a generated copy, not a
hardlink — see *Settled* below for why. The **directory** row (`skills/<skill>/`) stays a junction on
Windows and a symlink on macOS either way, per `link_config.py`'s `_file_link` vs. plain `Link`.

`hooks/powershell-tool-prompt.ps1` is a reference copy, same treatment as `settings.json`. The script
body is portable, but its *registration* — the `hooks.SessionStart`/`hooks.PreToolUse` block naming
`pwsh.exe`'s absolute path and this script's absolute path — is Windows-specific and user-specific, so
it stays in the live `~/.claude/settings.json` only. See "There is a PowerShell tool" in
`~/.agentic-workbench/machine.md`.

`hooks/ruff_on_edit.py` is the opposite case: portable script *and* portable registration, so it is
linked. The registration checks `.venv/bin/python` and `.venv/Scripts/python.exe`, covering POSIX and
Windows venv layouts. After an agent edits or creates a `.py` file it runs the project's own `.venv` ruff —
`check --fix`, then `format` — on the whole file; with no `.venv` or no ruff there it does nothing, and
it never installs. Formatting the whole file, not only the edited lines, is a deliberate choice: an
unformatted file shows formatter changes the edit did not make. Claude registers it through the
`hooks.PostToolUse` block in `settings.json` (merged by hand, like the rest of that file); Copilot
through `ruff-on-edit.copilot.json`, linked into `~/.copilot/hooks/`.

## Settings are merged, never linked

`~/.claude/settings.json` is never linked, on any machine. Two reasons, and only the first holds
everywhere:

- **Claude Code writes to that file itself.** A `/config` toggle, a model switch or the Bedrock setup
  wizard all land in it. Link it into this repo and those writes become commits; check out a branch and
  the machine's live settings change under it. That is machine-independent and is the standing reason.
- **On a provider-bound machine it also carries an `env` block** — `CLAUDE_CODE_USE_BEDROCK`,
  `AWS_REGION`, `AWS_PROFILE` and the provider-prefixed model IDs — which this repo deliberately does
  not hold, because this directory is shared unmodified and the block is sensitive.

**Whether a given machine is provider-bound is machine state and lives in
[`../machines/`](../machines/), never here.** `machines/windows-ema-pf5n4xe7.md` records one that is;
`machines/macos-workstation.md` records one that is not. Do not read a requirement off this file.

Three rules follow:

- **Never link, copy over, or regenerate `~/.claude/settings.json`.** Every route in [`setup/`](setup/)
  omits it deliberately. `ln -sfn` and `New-Item -Force` both replace the target rather than merging
  it, so either one silently drops whatever the live file held.
- **An `env` block does not move to `settings.local.json`.** Where one exists it stays in
  `settings.json`, which is its authoritative home.
- **The two files are allowed to differ**, and on a provider-bound machine they always will. A
  difference here is design, not drift.

### The merge procedure

On a new machine, or whenever this repo's copy gains a key, work through these six steps. **Steps 3 and
4 are the user's to type** — an agent runs 1, 2, 5 and 6 and stops.

**1. Back up, so a bad edit is one command from undone.** Run from anywhere:

```powershell
Copy-Item ~/.claude/settings.json ~/.claude/settings.json.bak
```

**2. Print the delta.** Run from the repo root. This reads both files and writes neither:

```
uv run python workstation/scripts/settings_delta.py
```

It prints one `add <key>: <value>` line per difference, or `in sync`, and exits 1 or 0 to match. An
object-valued key — `enabledPlugins`, `permissions` — is compared member by member, so
`permissions.defaultMode` is reported on its own. A list reports only the items the live one lacks.
[`../scripts/README.md`](../scripts/README.md#settings_deltapy) has the full contract.

**3. Add each reported key by hand**, in an editor, at the **top level** of the JSON object — a sibling
of `env`, never inside it. For an object-valued key, add the missing *members* and leave the rest alone.
A key the live file already has with a different value is a genuine choice: the repo copy is the shared
default, so take it unless this machine has a reason not to.

**4. Set the model IDs inside `env` if they are stale.** This is the one part of `env` that is a
preference rather than a compliance constraint, so it is edited in place — the block's **presence** is
what is mandatory, not the model it names. Note there are two independent settings and they are easy to
confuse:

| Key | Where | What it does |
|---|---|---|
| `model` | top level | what a session resolves to — the one that decides |
| `env.ANTHROPIC_MODEL` | inside `env` | the Bedrock model ID passed through to the provider |

Leave every other member of `env` — `CLAUDE_CODE_USE_BEDROCK`, `AWS_REGION`, `AWS_PROFILE` — exactly as
it is.

**5. Prove the file is still valid JSON, and — only on a provider-bound machine — that it still has its
`env` block.** Check this machine's file under [`../machines/`](../machines/) first: only a
provider-bound machine (Bedrock) is required to carry an `env` block at all; a subscription machine has
none, and that is correct, not a failure — see *Settings are merged, never linked* above. An editor can
leave a trailing comma that Claude Code reports only as a silent fallback to another provider:

```
uv run python workstation/scripts/settings_delta.py --env
```

It exits 2 if the file is not valid JSON. On a provider-bound machine, `env keys` must be non-empty and
`CLAUDE_CODE_USE_BEDROCK` must not be `None`; if either
fails, restore the `.bak` from step 1 and start again. On a machine that is not provider-bound, an empty
`env keys:` is expected — skip the rest of this step.

**6. Re-run step 2, and check the model IDs separately.** `in sync` on its own does **not** mean the
merge is complete, because step 2 compares only the keys the repo copy has — and the repo copy has no
`env` block at all. **Step 4 is invisible to it.** Measured on `EMA-PF5N4XE7` on 26 August 2026: step 2
printed `in sync` while `env.ANTHROPIC_MODEL` was still a superseded model ID. So read the model rows
of step 5's `--env` output too: `model`, `ANTHROPIC_MODEL`, `ANTHROPIC_DEFAULT_HAIKU_MODEL` and
`ANTHROPIC_SMALL_FAST_MODEL`.

`ANTHROPIC_SMALL_FAST_MODEL` is **deprecated** — `ANTHROPIC_DEFAULT_HAIKU_MODEL` replaces it. The probe
prints both so a settings file still carrying the old key is visible rather than silently ignored; a
machine showing a value under `ANTHROPIC_SMALL_FAST_MODEL` has a key to migrate. See
[`setup/README.md`](setup/README.md#2-claude-on-bedrock-windows).

Read the two IDs and confirm they name the models you intend — nothing can check that for you, since
there is no reference value in the repo to compare against. The merge is done when step 2 prints
`in sync` **and** those IDs are the current ones.

Then delete the backup, and record in [`../machines/`](../machines/) that the merge was done —
**measured, not assumed**, and recording both results rather than just the `in sync`.

Nothing in this procedure, and nothing anywhere in this repo, writes the live file.

## Setup on a new machine

**Start at [`setup/README.md`](setup/README.md)** — it indexes the four agent-and-provider routes
(Claude on macOS, Claude on Bedrock under Windows, Copilot on either) and carries what differs between
them, including what Copilot reads and where.

The link mechanism itself is per-platform, so those steps live in [`setup/`](setup/) and the index
points at them rather than repeating them:

| Platform | Route | Guide |
|---|---|---|
| macOS | symlinks | [`setup/macos.md`](setup/macos.md) |
| Windows | junctions (directories) + hardlinks (files) — symlinks need admin or Developer Mode | [`setup/windows.md`](setup/windows.md) |
| Linux | not written — no machine yet | — |

**Read the *Before you start* section of whichever applies.** Neither route touches
`~/.claude/settings.json` — that one is merged by hand, per the section above.

Adding a platform means one new file in `setup/` and one in [`../machines/`](../machines/).

### Check and repair the links

One command reports every path in the *Contents* table and writes nothing. Run it from the repo root:

```
python workstation/scripts/link_config.py
```

It exits non-zero unless every Claude link in the *Contents* table is live, distinguishes a *detached* copy
from a *diverged* one, and never touches `settings.json`. Add `--apply` to repair:

```
python workstation/scripts/link_config.py --apply
```

`--apply` repairs a detached link, whose content still matches. It **reports and skips** a diverged one
rather than overwriting it, because reconciling two edited copies is judgement work — confirm the live
side carries nothing unique, then use `--force`.

Pass `--agent copilot` to check or apply Copilot's global skills and
`~/.copilot/copilot-instructions.md`. Pass both agents to maintain both homes in one run.

**On Windows this is routine, not exceptional.** `CLAUDE.md`, `machine.md`, and Copilot's
`copilot-instructions.md` are hardlinks there, and a hardlink is severed both by `git checkout` and by
any atomic-saving editor — Zed, VS Code, and Claude Code's own `Edit` tool included. So **re-run
`--apply` for each configured agent after editing a linked file, and after any merge, branch switch or
pull that touches one.** Which side you edited makes no difference. The skill junctions are immune, as
is every symlink on macOS. Details in
[`setup/windows.md`](setup/windows.md#windows-traps).

### One surface ignores these links entirely

**Cowork sessions on the desktop skip a `~/.claude/CLAUDE.md` that is itself a symlink or a hard
link**, and skip a symlinked `~/.claude/rules/` directory or rule file pointing outside the working
directory. Claude Code's memory documentation states this directly. Every link this repo creates is one
of those, so in that surface the global instructions silently do not load — `link_config.py` still
reports every link healthy, because they *are*; it is the reader that declines them.

Nothing here detects it. The check is `/context` inside a Cowork session: if `CLAUDE.md` is missing
under **Memory files**, this is why. The documented way round it is an `@` import from a real file
rather than a link, which is also the route Windows users are pointed at when symlinks need admin.

## Install the skills as a plugin instead

**For the `SKILLS` tuple only** — the register-free skills, not this repo's own `skills/`. Both
Claude Code and Copilot CLI can install this directory as a plugin from a local-path marketplace,
with one command, OS-independent — no symlink-vs-junction branch, no `--apply`/`--force` cycle. This
is an *additional* route, not a replacement: `link_config.py` still serves this repo's own skills and
every machine that already relies on the linked route.

This directory is a plugin root for both tools at once, holding one shared `skills/` and two pairs of
manifests:

| File | For |
|---|---|
| `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Claude Code |
| `plugin.json`, `marketplace.json` | Copilot CLI (Agent Plugins 1.0 — same `skills/`, no `.claude-plugin/` prefix) |

Both pairs' `version` fields track `[project] version` in `pyproject.toml`, checked by
`workstation/scripts/tests/test_plugin_manifest.py`.

**Use the absolute path to your clone, not a relative one.** Both tools store whatever path you give
`marketplace add` and resolve it again on every later command — a relative path only works for as
long as you happen to run from the repo root, and silently breaks the first time you don't. Replace
`<agentic-workbench>` below with where you cloned this repo:

| Platform | Example |
|---|---|
| macOS | `/Users/<you>/Development/agentic-coding/agentic-workbench` |
| Windows | `C:\Users\<you>\Work\Development\agentic-coding\agentic-workbench` |

```sh
# Claude Code
claude plugin marketplace add <agentic-workbench>/workstation/agent
claude plugin install workbench-skills@agentic-workbench
claude plugin details workbench-skills      # confirm: every skill in .claude-plugin/plugin.json, enabled

# Copilot CLI
copilot plugin marketplace add <agentic-workbench>/workstation/agent
copilot plugin install workbench-skills@agentic-workbench
copilot plugin list                         # confirm: workbench-skills, enabled
```

Verified on Windows by removing and re-adding the marketplace at its absolute path: both tools
re-installed `workbench-skills` with every skill then in the manifest, enabled, `v0.1.0`.

Hooks, MCP servers and `settings.json` are deliberately **not** part of this plugin — they stay on
the hand-merge/link route above, since folding them in would touch the provider-bound `env` block
area this file already treats as sensitive.

## Deliberately not tracked

- `.env` in this directory — holds `ANTHROPIC_API_KEY`. Excluded by the repo's
  `.gitignore`; never relax that entry.
- **The `env` block of `~/.claude/settings.json`** — Bedrock endpoint, region, AWS profile and model
  IDs. Lives on the machine only, per *Settings are merged, never linked*. Never add it to this
  directory's `settings.json`.
- `~/.claude/plugins/` — reinstall with `/plugin`. Currently `pyright-lsp` from the
  `claude-plugins-official` marketplace (`anthropics/claude-plugins-official`).
- `~/.claude.json` — per-project state and auth material.
- `~/.claude/settings.local.json` — the machine-local override layer, by design.
- `~/.claude/projects/`, `history.jsonl`, `sessions/`, `__store.db` — full
  session transcripts. Never commit these.
- `~/.claude/cache/`, `file-history/`, `shell-snapshots/`,
  `telemetry/`, `usage-data/`, `backups/`, `daemon/`, `daemon.log`, `debug/`,
  `ide/`, `jobs/`, `plans/`, `session-env/`, `tasks/`, `paste-cache/`,
  `stats-cache.json`, `mcp-needs-auth-cache.json` — regenerable churn. Claude
  Code adds directories here over time; treat this list as illustrative, not
  exhaustive. Only the paths in the *Contents* table above are tracked.

## Settled

From the 2026-07-30 usage report, when `WORKING_PRACTICES.md` was folded into `CLAUDE.md`.

- **`settings.json` is merged, not linked — 2026-08-25.** Both `setup/` routes originally linked it,
  which would have overwritten the live Bedrock `env` block that the Windows machine is required to
  run under. The first fix proposed moving that block to `settings.local.json`; it was rejected,
  because the requirement is that the block sit in `settings.json` itself. (The rule outlived its
  original reason: Claude Code writes to that file on every machine, so it holds where no provider
  constraint applies.) So this is the one file in
  a directory built on linking that cannot be linked, and the two copies differ permanently by design.
  It follows the same rule as the rest of the split — the sensitive, machine-held part and the shared
  part have different lifetimes, so they cannot share a file — but the mechanism is a hand merge
  rather than an indirection, because a settings file has no include.

- **Machine state left this directory — 2026-08-25.** `CLAUDE.md` carried a Windows-only
  `## Environment` section while this README asserted "nothing here is machine-specific by design",
  and both were true at once, which is the contradiction that forced the split. State now lives in
  [`../machines/`](../machines/) and is *measured* by `../scripts/inventory.py` rather than written by
  hand; the two per-platform link blocks moved to [`setup/`](setup/). The line drawn is **lifetime**,
  not platform — see [`../machines/README.md`](../machines/README.md). A second machine is what exposed it, but one machine had the same defect — the `status:` field in
  every `install.md` was already unanswerable.

- **A `docsync` skill — delivered, in three parts.** The proposal was "reconcile the
  documents, verify every link and install command, report a per-file table, stop before
  committing". Link and path reconciliation is `review`'s `repo_check.py` (`links` plus
  `bare_paths`, on every push). Claim verification split again in 2026-08 along the line
  that actually matters, which turned out not to be *what* is checked but *what it costs*:
  `verify-docs`'s `verify_claims.py` settles mechanically anything a command can settle,
  and `verify-docs` the skill keeps the claims that need reading. The original split was
  drawn between subject matters; the durable one is drawn between free and expensive.

- **Deterministic claim verification runs on every push — 2026-08-24.** This reverses the
  line above's "on demand, never in front of every push", and the reversal is the point:
  that rule was about *cost*, not about claims. `verify_claims.py` calls no model, so the
  objection does not apply to it. Two things make it safe in a hook — it verifies only the
  markdown in the push (typically sub-second), and network-dependent
  checks stay behind `--online`, so a push never fails because someone else's site is
  down. A tool that is merely absent reports `UNVERIFIABLE` and does not block; only a
  `REFUTED` row, where documentation and reality disagree, refuses the push.
  `SKIP_VERIFY_CLAIMS=1` skips just that check.

- **Path exemptions live in the repo, not in the hook — 2026-08-24.** The hook is one file
  in this globally symlinked tree, reached by every repo that links it, so a glob written
  into it would silently exempt paths in unrelated repos. They go in `.verify-claims-allow`
  at the root of the repo being pushed: tracked, visible in a diff, inherited by nothing.
  No file means no globs. `.verify-flags-allow` beside it does the same for a flag that works
  but that no help text documents — `git diff --staged`, a synonym `git diff -h` never
  prints — kept separate because the first file is pinned to paths *meant* not to exist.
- **One component owns the exemptions — 2026-09-21.** `verify_claims.py` reads both files,
  applies them, and prints what it waived; the hook reads neither. It used to parse the path
  file and pass each glob back as `--allow`, and print its own count — a second parser of one
  format, and a second place the policy was stated. The notice now comes from the code that
  applies it, so it cannot drift from what the run did. The hook keeps *scope*: which markdown
  is in the push, which suites to run, and propagating the exit code.
- **`fix-findings` defers rather than restates — 2026-08-23.** It used to carry its own
  shorter procedure, and both of its differences from `review`'s Apply mode were defects:
  it said to apply *all* findings, dropping the rule that judgement calls are escalated
  rather than guessed, and it mandated conventional-commit messages for a repo whose
  commits contain none. It is now a pointer plus that one rule. A summary of a procedure
  is what an agent reads instead of the original, and it is the summary that goes stale.
- **A `PreToolUse` hook on Bash — declined 2026-08-22.** It would block global installs
  and home-directory scans mechanically instead of relying on key principle 3. Declined
  because the rules it would enforce are judgement-shaped, not pattern-shaped: a blanket
  Bash matcher cannot tell a project-scoped `uv add` from a global one without encoding
  the distinction itself, and a gate that blocks legitimate work gets bypassed and then
  ignored. The confirmation gates stay prose. Reopen this if the agent is actually
  observed breaking them — that evidence would change the answer.

- **Autonomous non-destructive delegation — 2026-09-18.** Agents may delegate bounded,
  non-destructive tasks when doing so improves the outcome, reduces latency, or preserves
  context. They state the objective and model tier, retain all confirmation gates, and keep
  pushes with the parent agent. A subagent may edit and make a local commit only within its
  explicit scope.

- **Windows file links became generated copies, not hardlinks — 2026-10-12.** `CLAUDE.md`,
  `copilot-instructions.md`, `machine.md` and the new `~/.agentic-workbench/AGENTS.md` all used
  `os.link()` on Windows, which severs on `git checkout` or any atomic-saving editor — the
  defect `link_config.py`'s *detached*/*diverged* split exists to catch. `link_config.py` already
  had the mechanism this needed, built for the project `CLAUDE.md`'s `@AGENTS.md` import: a
  `Link.content` field that `inspect()`/`apply()` treat as "this destination must hold exactly
  this text," generated rather than linked. `_file_link()` generalises it to every home-level
  file link, Windows only — macOS keeps the real symlink, which has no severance defect. This
  also lifts the hardlink's same-volume-as-`$HOME` requirement for these artifacts, and (since a
  plain file is neither a symlink nor a hardlink) sidesteps Cowork's existing skip of a
  `CLAUDE.md` that is itself a link resolving outside the working directory. Migration was free:
  an already-live hardlink's destination holds the same bytes as its source, so the moment
  `plan()` started setting `content=`, the existing copy read `linked` immediately.
- **Renaming `<repo>/.claude/` to `<repo>/.agentic-workbench/` — declined, 2026-10-12.**
  `.claude/skills/` and `.claude/CLAUDE.md` are not this repo's naming choice: they are Claude
  Code's own hardcoded discovery paths, and one of Copilot's three fixed project-scope skill
  paths. Renaming the folder doesn't make it neutral, it makes both tools stop finding anything
  there. The assistant-neutral authoring layer this was reaching for already exists —
  `skills/<name>/SKILL.md`, root `AGENTS.md` — and now has a home-scope counterpart,
  `~/.agentic-workbench/AGENTS.md`, in the entry above.
