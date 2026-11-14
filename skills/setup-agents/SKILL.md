---
name: setup-agents
description: Identify this machine and the AI coding assistants on it (Claude Code, GitHub Copilot CLI, VS Code, and others found on PATH), ask which to set up, whether Claude runs on AWS Bedrock or the user's own subscription, whether this workbench's instructions and skills should be global, and whether to continue to MCP server setup — then describe every change and either apply the links or hand the user the commands. Use when setting up a new machine, adding an assistant, switching Claude's provider, checking whether the global config is in place, or beginning workstation MCP setup. Not for installing or signing in to an assistant.
author: Achilleas Voutsas
version: 0.4.0
---

# Set up the agents on this machine

Check workstation status, detect agent configuration, ask, describe, then ask again. **Nothing on the machine changes
before the user answers step 4**, and even then this skill only ever writes links, the gitignored per-clone
`CLAUDE.md` (an `@AGENTS.md` import, with `--claude-md`), and a merge into the repo's own tracked `.mcp.json`
(with `--mcp`) — never a client's user-scope config.

This skill orchestrates recorded routes; it does not carry them. Which agent reads what, and the
provider steps, are in [`workstation/agent/setup/README.md`](../../workstation/agent/setup/README.md).
The linker is [`workstation/scripts/link_config.py`](../../workstation/scripts/link_config.py). Where
this file and those disagree, they win — fix this file.

Both scripts are stdlib-only. Every command below writes `<python>`: substitute `uv run --no-sync python`
from the repository root when its `.venv` exists, and otherwise the bootstrap interpreter, `python3` on macOS and `python` on Windows. That fallback is
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

Run the shared readiness pre-step:

```sh
<python> workstation/scripts/status.py
```

Show its complete table. A `NOT READY` result stops setup until its required corrective actions are
complete. `READY WITH ACTIONS` does not stop agent setup; ask only about optional tools the user wants.
Authentication is not assessed here or elsewhere in this setup.
Common dependencies marked `external provisioning` are report-only: do not offer to install them.

Then detect the assistants and their current configuration:

```sh
<python> skills/setup-agents/scripts/detect.py
```

Show the user its three tables as printed. Add `--json` when you need to branch on a value.

| Detected | Then |
|---|---|
| Machine note **absent** | Say so. The `machine.md` link — made for Claude and Copilot alike — stays `no_source` until it exists. Creating it is [`workstation/machines/README.md` § *Adding a machine*](../../workstation/machines/README.md#adding-a-machine); ask the user for the id first — the file is pushed, and a hostname is often a person's name. |
| No configurable assistant on `PATH` | Report it and stop. |

## 2. Ask

One round, with only the questions that apply. Use a structured question tool where the harness has one.

| Question | Ask when | Options |
|---|---|---|
| Which assistants should this set up? (multi-select) | always | each **configurable** assistant detect found; name the report-only ones in the question text as not configurable |
| Should Claude Code use AWS Bedrock or your own subscription? | Claude Code selected | Bedrock · Own subscription. Quote detect's current provider in the question, so a switch reads as one. |
| Should this workbench's instructions and skills be global? | always | Yes — link into `~/.claude` and `~/.copilot` · No — this repo only |
| Set up documented MCP servers after agent setup? | always | Yes — invoke `setup-mcp-servers` after this skill completes · No — stop after agent setup |
| Do you want to install missing optional toolchain products? | status reports optional items needing action | All missing items · selected items · none. Give the exact corrective actions from the status report; the user runs them. |

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
Pass `--mcp` always too: it merges `workstation/mcp/.mcp.json` — every MCP server this repo
documents — into `<repo>/.mcp.json`, the file Claude Code (project scope) and Copilot CLI
(workspace scope) both read, so neither assistant selection nor the global answer changes it.

```sh
<python> workstation/scripts/link_config.py --project --claude-md --mcp --agent claude --agent copilot --json
```

| Status | The row says |
|---|---|
| `linked` | no change |
| `missing` | create `dest` → `source`: a symlink on macOS; on Windows a junction for a directory, a hardlink for a file |
| `detached` | replace what is at `dest` with a link; `detail` names what is there now |
| `diverged`, `occupied` | **skipped** — `dest` holds content the repo lacks. Give `diff <dest> <source>` or `ls <dest>`; reconciling is the user's |
| `no_source` | blocked until the machine note exists (step 1) |

The `--mcp` output is a separate table, one row per server rather than per file: `missing` means
add it to `<repo>/.mcp.json`; `diverged` means the live entry's value differs from the catalog —
same skip-and-reconcile rule as a diverged file, never overwritten even with `--force`.

State the consequence with the list: once linked, an edit to `~/.claude/CLAUDE.md` or a linked skill
writes into this repo; once merged, an edit to `workstation/mcp/.mcp.json` and a re-run of `--apply`
updates the tracked `<repo>/.mcp.json` every clone shares.

**User steps** — theirs whichever mode they pick in step 4:

| Answer | User steps | Route |
|---|---|---|
| Claude, own subscription | If detect found provider variables, name them — the user removes them from the `env` block. Authentication remains external. | setup README §1 |
| Claude, Bedrock | After AWS access and credentials are provisioned externally, configure the Bedrock provider and pin `ANTHROPIC_DEFAULT_OPUS_MODEL`, `_SONNET_`, `_HAIKU_`. | setup README §2 |
| Claude, global | add the keys detect lists as differing from `workstation/agent/settings.json` | `macos.md` / `windows.md` § *Settings* |
| VS Code, global | set `"chat.useClaudeMdFile": true` in the user settings file detect named | setup README §3 |
| Optional tool installation requested | commands for the selected missing workstation tools from the status report | `workstation/cli/<tool>/install.md` |

Present one table: `# | change | path | who runs it | status now`.

**Nothing to change — stop here.** When every link row and every MCP server row reads `linked` and
every user step's *status now* is already done — detect lists no differing settings keys, the
provider matches the answer, VS Code's flag is `true` where it was asked for, and the status report
has no selected optional action —
skip step 4.
Say that nothing needs changing, quote the `N of N linked` line, and give the *Verify* checks below.
Do not ask *apply or hand over*: both would run a no-op. Step 2's questions are still asked, because
the answers decide what step 3 checks. If the user selected MCP setup, continue to step 5 instead of
ending the interaction.

## 4. Apply, or hand over

Ask: *should I apply the link changes, or give you the commands to run?* Say in the question that the
user steps stay theirs either way.

**Apply**

1. `git status -s workstation/agent`. If it is dirty, say so before linking — linking makes
   those edits live.
2. `<python> workstation/scripts/link_config.py --apply` with the same flags as step 3 (including `--mcp`).
3. Re-run it without `--apply` and quote the `N of N linked` line. Anything short of that is
   reported, never retried with `--force`.
4. Give the user steps from step 3, in order, as commands.
5. Offer — do not do — recording the result in the machine note: its *Claude Code config* table, its
   provider line, and the Copilot skills finding.

**Hand over** — write nothing. One fenced block in this platform's shell, then the user steps:

```sh
cd <repo>
git status -s workstation/agent
<python> workstation/scripts/link_config.py --apply --project --claude-md --mcp --agent claude --agent copilot
<python> workstation/scripts/link_config.py --project --claude-md --mcp --agent claude --agent copilot
```

Substitute `<python>` before handing the block over, and on Windows write it in PowerShell. Hand over `link_config.py`, never hand-written
`ln -s` / `New-Item` lines: it derives both skill lists, so neither can go stale.

## Verify

| Assistant | Check, in a session |
|---|---|
| Claude Code | `/context` lists `CLAUDE.md` under Memory files; `/status` shows the chosen provider |
| Copilot CLI | `/skills` lists the linked skills |
| VS Code | Chat's loaded context lists the instruction file |
| Workstation | User re-runs `<python> workstation/scripts/status.py`; required dependencies and requested tools report `installed` |

## 5. Optional MCP setup

If the user selected *No* in step 2, stop after this skill's agent setup and verification.

If the user selected *Yes*, invoke the global `setup-mcp-servers` skill **only after** completing this
skill's apply/hand-over or no-op branch. Do not preselect a server, forward an authentication value, or
combine its prompts with this skill's prompt round: it performs fresh read-only discovery and asks its
own route-specific, non-secret questions. Its user-run registration and sign-in rules remain in force.
