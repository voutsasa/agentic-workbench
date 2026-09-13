---
name: setup-agents
description: Identify this machine and the AI coding assistants on it (Claude Code, GitHub Copilot CLI, VS Code, and others found on PATH), ask which to set up, whether Claude runs on AWS Bedrock or the user's own subscription, and whether this workbench's instructions and skills should be global — then describe every change and either apply the links or hand the user the commands. Use when setting up a new machine, adding an assistant, switching Claude's provider, or checking whether the global config is in place. Not for installing or signing in to an assistant.
---

# Set up the agents on this machine

Detect, ask, describe, then ask again. **Nothing on the machine changes before the user answers
step 4**, and even then the only thing this skill ever writes is links.

This skill orchestrates recorded routes; it does not carry them. Which agent reads what, and the
provider steps, are in [`workstation/agent/setup/README.md`](../../workstation/agent/setup/README.md).
The linker is [`workstation/scripts/link_config.py`](../../workstation/scripts/link_config.py). Where
this file and those disagree, they win — fix this file.

Both scripts are stdlib-only and run without a venv — `python3` on macOS, `python` on Windows. That is
the exception recorded in [`workstation/scripts/README.md`](../../workstation/scripts/README.md).

## Never, whatever the user answers

- **Write a settings file** — `~/.claude/settings.json`, VS Code's `settings.json`,
  `~/.copilot/settings.json`. Name the keys; the user merges them.
- **Pass `--force`** to `link_config.py`, unless the user asks for it after seeing the `diff`.
- **Install, upgrade or sign in to an assistant.** One not on `PATH` is reported absent, and the skill
  stops there for that assistant.
- **Set up a report-only assistant.** No route is recorded for it. Say so.

## 1. Detect

```sh
python3 skills/setup-agents/scripts/detect.py
```

Show the user its three tables as printed. Add `--json` when you need to branch on a value.

| Detected | Then |
|---|---|
| Machine note **absent** | Say so. Claude's `machine.md` link stays `no_source` until it exists. Creating it is [`workstation/machines/README.md` § *Adding a machine*](../../workstation/machines/README.md#adding-a-machine); ask the user for the id first — the file is pushed, and a hostname is often a person's name. |
| No configurable assistant on `PATH` | Report it and stop. |

## 2. Ask

One round, with only the questions that apply. Use a structured question tool where the harness has one.

| Question | Ask when | Options |
|---|---|---|
| Which assistants should this set up? (multi-select) | always | each **configurable** assistant detect found; name the report-only ones in the question text as not configurable |
| Should Claude Code use AWS Bedrock or your own subscription? | Claude Code selected | Bedrock · Own subscription. Quote detect's current provider in the question, so a switch reads as one. |
| Should this workbench's instructions and skills be global? | always | Yes — link into `~/.claude` and `~/.copilot` · No — this repo only |

"No" still leaves this repo working for both, through the project links in step 3.

## 3. Describe the changes

Build the list from evidence, not from this file.

**Links.** Run the report, read-only. Pass `--project` always: it links this repo's own skills into
`.claude/skills/`, which Claude Code and Copilot both read at project scope, and a fresh clone has none
because `.claude/` is gitignored. When the answer to *global* is yes, add one `--agent` per selected
assistant that links: Claude Code → `claude`, Copilot CLI → `copilot`. VS Code has no links.

```sh
python3 workstation/scripts/link_config.py --project --agent claude --agent copilot --json
```

| Status | The row says |
|---|---|
| `linked` | no change |
| `missing` | create `dest` → `source`: a symlink on macOS; on Windows a junction for a directory, a hardlink for a file |
| `detached` | replace what is at `dest` with a link; `detail` names what is there now |
| `diverged`, `occupied` | **skipped** — `dest` holds content the repo lacks. Give `diff <dest> <source>` or `ls <dest>`; reconciling is the user's |
| `no_source` | blocked until the machine note exists (step 1) |

State the consequence with the list: once linked, an edit to `~/.claude/CLAUDE.md` or a linked skill
writes into this repo.

**User steps** — theirs whichever mode they pick in step 4:

| Answer | User steps | Route |
|---|---|---|
| Claude, own subscription | `claude`, sign in, `/status`. If detect found provider variables, name them — the user removes them from the `env` block. | setup README §1 |
| Claude, Bedrock | AWS model access and IAM; `export AWS_PROFILE=<profile>`, then `aws sso login`; `/setup-bedrock`, typed in full; pin `ANTHROPIC_DEFAULT_OPUS_MODEL`, `_SONNET_`, `_HAIKU_`. §2 is written in PowerShell, where the first is `$env:AWS_PROFILE = "<profile>"`. | setup README §2 |
| Claude, global | add the keys detect lists as differing from `workstation/agent/settings.json` | `macos.md` / `windows.md` § *Settings* |
| Copilot CLI | `copilot login` if not signed in | setup README §3 |
| VS Code, global | set `"chat.useClaudeMdFile": true` in the user settings file detect named | setup README §3 |

Present one table: `# | change | path | who runs it | status now`.

## 4. Apply, or hand over

Ask: *should I apply the link changes, or give you the commands to run?* Say in the question that the
user steps stay theirs either way.

**Apply**

1. `git status -s workstation/agent`. If it is dirty, say so before linking — linking makes
   those edits live.
2. `python3 workstation/scripts/link_config.py --apply` with the same flags as step 3.
3. Re-run it without `--apply` and quote the `N of N linked` line. Anything short of that is
   reported, never retried with `--force`.
4. Give the user steps from step 3, in order, as commands.
5. Offer — do not do — recording the result in the machine note: its *Claude Code config* table, its
   provider line, and the Copilot skills finding.

**Hand over** — write nothing. One fenced block in this platform's shell, then the user steps:

```sh
cd <repo>
git status -s workstation/agent
python3 workstation/scripts/link_config.py --apply --project --agent claude --agent copilot
python3 workstation/scripts/link_config.py --project --agent claude --agent copilot
```

On Windows it is `python`, not `python3`, in PowerShell. Hand over `link_config.py`, never hand-written
`ln -s` / `New-Item` lines: it derives both skill lists, so neither can go stale.

## Verify

| Assistant | Check, in a session |
|---|---|
| Claude Code | `/context` lists `CLAUDE.md` under Memory files; `/status` shows the chosen provider |
| Copilot CLI | `/skills` lists the linked skills |
| VS Code | Chat's loaded context lists the instruction file |
