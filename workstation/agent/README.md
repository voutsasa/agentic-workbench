# Agent config

Hand-authored Claude Code config, versioned here and linked into `~/.claude/` so it is not scattered
through a home directory.

**Everything in this directory is shared by every machine, unmodified.** That is the invariant the rest
of the tree is arranged around, and it has three consequences:

- Anything about the *state* of a machine — paths, shell quirks, which tools run, what is broken —
  belongs in [`../machines/`](../machines/), not in `CLAUDE.md`. See
  [`../machines/README.md`](../machines/README.md) for the test.
- **`settings.json` here is a reference, not a link target.** The live `~/.claude/settings.json` must
  keep its Bedrock `env` block, so it is the one file in this directory that is merged key-by-key
  rather than linked — see *Settings are merged, never linked* below.
- Anything else machine-local, and not compliance-bound, belongs in `~/.claude/settings.local.json`,
  which is untracked by design.

## Contents

| Path | Goes to | How |
|---|---|---|
| `CLAUDE.md` | `~/.claude/CLAUDE.md` | linked |
| `settings.json` | `~/.claude/settings.json` | **merged by hand — never linked** |
| `skills/review/` | `~/.claude/skills/review` | linked |
| `skills/python-quality/` | `~/.claude/skills/python-quality` | linked |
| `skills/verify-docs/` | `~/.claude/skills/verify-docs` | linked |
| `skills/fix-findings/` | `~/.claude/skills/fix-findings` | linked |
| `../machines/<platform>-<host>.md` | `~/.claude/machine.md` | linked |
| `hooks/powershell-tool-prompt.ps1` | `~/.claude/hooks/powershell-tool-prompt.ps1` | **reference copy — copied by hand, never linked** |

The last row before this one is the indirection that keeps this directory platform-neutral: one fixed
path, different content per machine, so `CLAUDE.md` can point at machine truth without naming a
platform.

`hooks/powershell-tool-prompt.ps1` is a reference copy, same treatment as `settings.json`. The script
body is portable, but its *registration* — the `hooks.SessionStart`/`hooks.PreToolUse` block naming
`pwsh.exe`'s absolute path and this script's absolute path — is Windows-specific and user-specific, so
it stays in the live `~/.claude/settings.json` only. See "There is a PowerShell tool" in
`~/.claude/machine.md`.

## Settings are merged, never linked

`~/.claude/settings.json` **must keep its Bedrock `env` block** — `CLAUDE_CODE_USE_BEDROCK`,
`AWS_REGION`, `AWS_PROFILE` and the Bedrock-prefixed model IDs. Routing this account's traffic through
Bedrock is a **compliance requirement, not a preference**, which sets three rules:

- **Never link, copy over, or regenerate `~/.claude/settings.json`.** Every route in [`setup/`](setup/)
  omits it deliberately. `ln -sfn` and `New-Item -Force` both replace the target rather than merging
  it, so either one silently drops the `env` block and the session falls back to another provider.
- **The `env` block does not move to `settings.local.json`.** It stays in `settings.json`, which is its
  authoritative home.
- **It is deliberately absent from this repo**, because this directory is shared unmodified and the
  block is sensitive. The two files are therefore *expected* to differ for ever — that difference is
  the design, not drift.

### The merge procedure

On a new machine, or whenever this repo's copy gains a key, work through these six steps. **Steps 3 and
4 are the user's to type** — an agent runs 1, 2, 5 and 6 and stops.

**1. Back up, so a bad edit is one command from undone.** Run from anywhere:

```powershell
Copy-Item ~/.claude/settings.json ~/.claude/settings.json.bak
```

**2. Print the delta.** Run from the repo root. This reads both files and writes neither:

```
python -c "import json,pathlib;L=json.loads((pathlib.Path.home()/'.claude/settings.json').read_text());R=json.loads(pathlib.Path('workstation/agent/settings.json').read_text());print('\n'.join(f'add {k}: {json.dumps(v)}' for k,v in R.items() if L.get(k)!=v) or 'in sync')"
```

The comparison is **one level deep**, so a key whose value is an object — `enabledPlugins`,
`permissions` — reports as a whole even when only one member differs. Read it as *"reconcile this key"*,
not *"replace this key"*.

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

**5. Prove the file is still valid JSON and still has its `env` block.** An editor can leave a trailing
comma that Claude Code reports only as a silent fallback to another provider:

```powershell
python -c "import json,pathlib;d=json.loads((pathlib.Path.home()/'.claude/settings.json').read_text());print('valid JSON'); print('env keys:', sorted(d.get('env',{}))); print('BEDROCK:', d.get('env',{}).get('CLAUDE_CODE_USE_BEDROCK'))"
```

`env keys:` must be non-empty and `BEDROCK:` must not be `None`. If either fails, restore the `.bak`
from step 1 and start again.

**6. Re-run step 2, and check the model IDs separately.** `in sync` on its own does **not** mean the
merge is complete, because step 2 compares only the keys the repo copy has — and the repo copy has no
`env` block at all. **Step 4 is invisible to it.** Measured on `EMA-PF5N4XE7` on 26 August 2026: step 2
printed `in sync` while `env.ANTHROPIC_MODEL` was still a superseded model ID. So run both:

```powershell
python -c "import json,pathlib;d=json.loads((pathlib.Path.home()/'.claude/settings.json').read_text());e=d.get('env',{});print('model        :',d.get('model'));print('ANTHROPIC_MODEL:',e.get('ANTHROPIC_MODEL'));print('SMALL_FAST   :',e.get('ANTHROPIC_SMALL_FAST_MODEL'))"
```

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
| Windows | junctions (directories) + hardlinks (files) — symlinks need admin | [`setup/windows.md`](setup/windows.md) |
| Linux | not written — no machine yet | — |

**Read the *Before you start* section of whichever applies.** Neither route touches
`~/.claude/settings.json` — that one is merged by hand, per the section above.

Adding a platform means one new file in `setup/` and one in [`../machines/`](../machines/).

### Check and repair the links

One command reports every path in the *Contents* table and writes nothing. Run it from the repo root:

```
python workstation/scripts/link_config.py
```

It exits non-zero unless all six are live, distinguishes a *detached* copy from a *diverged* one, and
never touches `settings.json`. Add `--apply` to repair:

```
python workstation/scripts/link_config.py --apply
```

`--apply` repairs a detached link, whose content still matches. It **reports and skips** a diverged one
rather than overwriting it, because reconciling two edited copies is judgement work — confirm the live
side carries nothing unique, then use `--force`.

**On Windows this is routine, not exceptional.** `CLAUDE.md` and `machine.md` are hardlinks there, and a
hardlink is severed both by `git checkout` and by any atomic-saving editor — Zed, VS Code, and Claude
Code's own `Edit` tool included. So **re-run `--apply` after editing either file, and after any merge,
branch switch or pull that touches them.** Which side you edited makes no difference. The four skill
junctions are immune, as are all six symlinks on macOS. Details in
[`setup/windows.md`](setup/windows.md#windows-traps).

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
  which would have overwritten a live Bedrock `env` block that Claude Code is required to run under
  for compliance. The first fix proposed moving that block to `settings.local.json`; it was rejected,
  because the requirement is that the block sit in `settings.json` itself. So this is the one file in
  a directory built on linking that cannot be linked, and the two copies differ permanently by design.
  It follows the same rule as the rest of the split — the sensitive, machine-held part and the shared
  part have different lifetimes, so they cannot share a file — but the mechanism is a hand merge
  rather than an indirection, because a settings file has no include.

- **Machine state left this directory — 2026-08-25.** `CLAUDE.md` carried a Windows-only
  `## Environment` section while this README asserted "nothing here is machine-specific by design",
  and both were true at once, which is the contradiction that forced the split. State now lives in
  [`../machines/`](../machines/) and is *measured* by `../scripts/inventory.py` rather than written by
  hand; the two per-platform link blocks moved to [`setup/`](setup/). The line drawn is **lifetime**,
  not platform: policy never expires, a route expires slowly, state expires constantly. Putting all
  three in one file meant the slowest-changing content was edited at the rate of the fastest.
  A second machine is what exposed it, but one machine had the same defect — the `status:` field in
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
  markdown in the push (~0.3s, against ~18s for the whole repo), and network-dependent
  checks stay behind `--online`, so a push never fails because someone else's site is
  down. A tool that is merely absent reports `UNVERIFIABLE` and does not block; only a
  `REFUTED` row, where documentation and reality disagree, refuses the push.
  `SKIP_VERIFY_CLAIMS=1` skips just that check.

- **Path exemptions live in the repo, not in the hook — 2026-08-24.** The hook is one file
  in this globally symlinked tree, reached by every repo that links it, so a glob written
  into it would silently exempt paths in unrelated repos. They go in `.verify-claims-allow`
  at the root of the repo being pushed: tracked, visible in a diff, inherited by nothing.
  No file means no globs, and the hook prints the exemptions in force before it runs.
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

## Open ideas

Not adopted, not binding:

- **Task agents for repo exploration** — a compact proposal instead of scrolling directory
  listings. Note this pulls against `CLAUDE.md`'s "don't spawn agents I didn't ask for".
