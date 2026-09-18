---
name: setup-agents
description: Identify this machine and the AI coding assistants on it (Claude Code, GitHub Copilot CLI, VS Code, and others found on PATH), ask which to set up, whether Claude runs on AWS Bedrock or the user's own subscription, and whether this workbench's instructions and skills should be global — then describe every change and either apply the links or hand the user the commands. Use when setting up a new machine, adding an assistant, switching Claude's provider, or checking whether the global config is in place. Not for installing or signing in to an assistant.
---

# Set up the agents on this machine

Detect agents and the toolchain, ask, describe, then ask again. **Nothing on the machine changes
before the user answers step 4**, and even then the only thing this skill ever writes is links.

This skill orchestrates recorded routes; it does not carry them. Which agent reads what, and the
provider steps, are in [`workstation/agent/setup/README.md`](../../workstation/agent/setup/README.md).
The linker is [`workstation/scripts/link_config.py`](../../workstation/scripts/link_config.py). Where
this file and those disagree, they win — fix this file.

Both scripts are stdlib-only. Every command below writes `<python>`: substitute the repository's
`.venv` interpreter when it exists — `.venv/bin/python`, or `.venv\Scripts\python.exe` on Windows —
and otherwise the bootstrap interpreter, `python3` on macOS and `python` on Windows. That fallback is
recorded in [`workstation/scripts/README.md`](../../workstation/scripts/README.md).

## Never, whatever the user answers

- **Write a settings file** — `~/.claude/settings.json`, VS Code's `settings.json`,
  `~/.copilot/settings.json`. Name the keys; the user merges them.
- **Pass `--force`** to `link_config.py`, unless the user asks for it after seeing the `diff`.
- **Install, upgrade or sign in to an assistant.** One not on `PATH` is reported absent, and the skill
  stops there for that assistant.
- **Install or upgrade a CLI tool or its dependencies.** Give the user the recorded commands only.
- **Set up a report-only assistant.** No route is recorded for it. Say so.

## 1. Detect

```sh
<python> skills/setup-agents/scripts/detect.py
```

Show the user its three tables as printed. Add `--json` when you need to branch on a value.

| Detected | Then |
|---|---|
| Machine note **absent** | Say so. Claude's `machine.md` link stays `no_source` until it exists. Creating it is [`workstation/machines/README.md` § *Adding a machine*](../../workstation/machines/README.md#adding-a-machine); ask the user for the id first — the file is pushed, and a hostname is often a person's name. |
| No configurable assistant on `PATH` | Report it and stop. |

### Assess the CLI toolchain

Run the inventory with the same `<python>` choice:

```sh
<python> workstation/scripts/inventory.py
```

Show its complete table. `installed` means the version probe worked; `absent` means the product is
missing. `blocked` and `error` are not install requests: report their detail and consult that tool's
`quick_start.md` and `install.md` for the non-installing diagnostic or required runtime dependency.
For each product the user wants to use, include any required dependency named in those files, separating
it from optional components such as extra browsers or OCR languages.

## 2. Ask

One round, with only the questions that apply. Use a structured question tool where the harness has one.

| Question | Ask when | Options |
|---|---|---|
| Which assistants should this set up? (multi-select) | always | each **configurable** assistant detect found; name the report-only ones in the question text as not configurable |
| Should Claude Code use AWS Bedrock or your own subscription? | Claude Code selected | Bedrock · Own subscription. Quote detect's current provider in the question, so a switch reads as one. |
| Should this workbench's instructions and skills be global? | always | Yes — link into `~/.claude` and `~/.copilot` · No — this repo only |
| Do you want to install missing toolchain products or required dependencies? | inventory reports `absent`, or a needed product lacks a required dependency | All missing items · selected items · none. Give the exact platform commands from the relevant `install.md`; the user runs them. |

"No" still leaves this repo working for both, through the project links in step 3.

## 3. Describe the changes

Build the list from evidence, not from this file.

**Links.** Run the report, read-only. Pass `--project` always: it links this repo's own skills into
`.claude/skills/`, which Claude Code and Copilot both read at project scope, and a fresh clone has none
because `.claude/` is gitignored. Add `--claude-md` when Claude Code is selected, global or not: it
writes the gitignored root `CLAUDE.md` (`@AGENTS.md`), Claude Code's only route to the repo
instructions. Leave it out when only Copilot is selected — Copilot CLI reads `AGENTS.md` and `CLAUDE.md`
both, so the file would load the instructions twice. When the answer to *global* is yes, add one `--agent` per selected
assistant that links: Claude Code → `claude`, Copilot CLI → `copilot`. VS Code has no links.

```sh
<python> workstation/scripts/link_config.py --project --claude-md --agent claude --agent copilot --json
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
| Toolchain installation requested | commands for the selected missing products and required dependencies, from each tool's `install.md` | `workstation/cli/<tool>/install.md` |

Present one table: `# | change | path | who runs it | status now`.

## 4. Apply, or hand over

Ask: *should I apply the link changes, or give you the commands to run?* Say in the question that the
user steps stay theirs either way.

**Apply**

1. `git status -s workstation/agent`. If it is dirty, say so before linking — linking makes
   those edits live.
2. `<python> workstation/scripts/link_config.py --apply` with the same flags as step 3.
3. Re-run it without `--apply` and quote the `N of N linked` line. Anything short of that is
   reported, never retried with `--force`.
4. Give the user steps from step 3, in order, as commands.
5. Offer — do not do — recording the result in the machine note: its *Claude Code config* table, its
   provider line, and the Copilot skills finding.

**Hand over** — write nothing. One fenced block in this platform's shell, then the user steps:

```sh
cd <repo>
git status -s workstation/agent
<python> workstation/scripts/link_config.py --apply --project --claude-md --agent claude --agent copilot
<python> workstation/scripts/link_config.py --project --claude-md --agent claude --agent copilot
```

Substitute `<python>` before handing the block over, and on Windows write it in PowerShell. Hand over `link_config.py`, never hand-written
`ln -s` / `New-Item` lines: it derives both skill lists, so neither can go stale.

## Verify

| Assistant | Check, in a session |
|---|---|
| Claude Code | `/context` lists `CLAUDE.md` under Memory files; `/status` shows the chosen provider |
| Copilot CLI | `/skills` lists the linked skills |
| VS Code | Chat's loaded context lists the instruction file |
| CLI toolchain | User re-runs `<python> workstation/scripts/inventory.py`; requested products report `installed` |
