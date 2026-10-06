# Agent setup — the four routes

Which agent, on which machine, against which provider. Four combinations, each a short list of steps
on top of the per-platform link route.

| Route | Agent | Platform | Provider | Section |
|---|---|---|---|---|
| 1 | Claude Code | macOS | Claude subscription | [Claude on macOS](#1-claude-on-macos) |
| 2 | Claude Code | Windows | Amazon Bedrock | [Claude on Bedrock, Windows](#2-claude-on-bedrock-windows) |
| 3 | GitHub Copilot | macOS | GitHub | [Copilot on macOS](#3-copilot-on-macos) |
| 4 | GitHub Copilot | Windows | GitHub | [Copilot on Windows](#4-copilot-on-windows) |

**This file carries only what differs by agent and provider.** The mechanics of putting the links in
place — symlinks on macOS, junctions plus hardlinks on Windows — stay in [`macos.md`](macos.md) and
[`windows.md`](windows.md), which each route points at rather than repeating. A command written twice
is a command that drifts.

Every step marked **user** changes your machine and is yours to run; see *The user installs; the agent
records* in [`../../../AGENTS.md`](../../../AGENTS.md#the-user-installs-the-agent-records).

## What each agent reads

The two agents converge on more than they diverge. The instruction file is shared outright, and the
skill format is identical — only the parent directory differs.

| | Claude Code | GitHub Copilot |
|---|---|---|
| **User instructions** | `~/.claude/CLAUDE.md` | CLI: `~/.copilot/copilot-instructions.md`; VS Code: `~/.claude/CLAUDE.md` once `chat.useClaudeMdFile` is on |
| **Project instructions** | `CLAUDE.md` or `.claude/CLAUDE.md`, at the project root | `.github/copilot-instructions.md`, `AGENTS.md`; the CLI and cloud agent also `CLAUDE.md` and `GEMINI.md`, the CLI `.claude/CLAUDE.md` too. VS Code Chat reads `CLAUDE.md` only once `chat.useClaudeMdFile` is on |
| **Skills** | `~/.claude/skills/<name>/SKILL.md` | `~/.copilot/skills/<name>/SKILL.md`; per project `.github/skills/`, `.agents/skills/`, `.claude/skills/` |
| **Settings** | `~/.claude/settings.json` | VS Code `settings.json`; CLI `~/.copilot/settings.json` |

Two consequences worth knowing before you start:

- **Claude Code reads `CLAUDE.md` and nothing else.** That is why this repo's
  [`../AGENT-INSTRUCTIONS.md`](../AGENT-INSTRUCTIONS.md) is *linked to* `~/.claude/CLAUDE.md` rather
  than renamed at the destination. The source name is ours; the destination name is Claude Code's.
- **Copilot reads `.claude/skills/<name>/` at project scope.** A repo that already carries Claude
  skills needs no second copy for Copilot.

---

## 1. Claude on macOS

Claude subscription, no provider configuration.

### Steps

1. **Record the machine** — a machine note is what every later session reads for paths and blockers:

   ```sh
   python workstation/scripts/inventory.py --host <id>   # python3 on macOS
   ```

   Paste the table it prints into `workstation/machines/macos-<id>.md` and add a row to
   [`../../machines/README.md`](../../machines/README.md).

2. **Link the config** — follow [`macos.md` § *Link it*](macos.md#link-it), which carries the
   commands, and pass `--hooks` there so the ruff post-edit hook is linked too.

   What it puts in place: one symlink per skill, `AGENT-INSTRUCTIONS.md` → `~/.claude/CLAUDE.md`,
   the machine note → `~/.agentic-workbench/machine.md`, and (with `--hooks`) `hooks/ruff_on_edit.py` →
   `~/.claude/hooks/`. `settings.json` is not among them, by design.

3. **Settings — merge by hand, never link.** (**user**) `settings.json` is excluded from the plan by
   design; `link_config.py` raises rather than emit it. Merge the keys you want from
   [`../settings.json`](../settings.json) into `~/.claude/settings.json` yourself.

4. **Sign in.** (**user**) Run `claude` and log in with the Claude account. A subscription needs no
   `env` block and no provider variables — that is the whole of the provider configuration here.

5. **Install the push gate** in each repo that should run it (**user**) — the command is in
   [`macos.md` § *The pre-push gate*](macos.md#the-pre-push-gate).

### Verify

Re-run the link report from [`macos.md`](macos.md#verify) and expect **all links reported live**
(`N of N linked`, where N is however many `link_config.py`'s `SKILLS` tuple implies).

Then in a session, `/context` and check the list under **Memory files**. If `CLAUDE.md` is absent
there, Claude cannot see it, however healthy the symlink looks.

---

## 2. Claude on Bedrock, Windows

Two independent halves: the same config links as route 1, plus AWS. Do the AWS half second — it is
the half that can fail for reasons outside this repo.

### Prerequisites — AWS (**user**)

1. **Enable the models.** In the Amazon Bedrock console, open the Model catalog, select an Anthropic
   model, and submit the use case form. Once per AWS account; access is granted on submission.

2. **IAM.** The role needs `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`,
   `bedrock:ListInferenceProfiles` and `bedrock:GetInferenceProfile`, plus
   `aws-marketplace:ViewSubscriptions` and `aws-marketplace:Subscribe`.

3. **Credentials.** Claude Code uses the default AWS SDK credential chain. An SSO profile:

   ```powershell
   aws sso login --profile <profile>
   $env:AWS_PROFILE = "<profile>"
   ```

### Steps

1. **Record the machine**, as route 1 step 1, into `workstation/machines/windows-<id>.md`.

2. **Link the config** — follow [`windows.md`](windows.md). Read its *Stop: read this before running
   anything* section first. Directories become junctions and files become hardlinks, both of which
   work unelevated; the clone must sit on the **same volume as `$HOME`**, because a hardlink cannot
   cross volumes.

3. **Configure Bedrock.** (**user**) Run `claude`, choose **3rd-party platform → Amazon Bedrock**, and
   follow the wizard. In an existing session the command is `/setup-bedrock`; type it in full, since
   it stays hidden from the command menu until `CLAUDE_CODE_USE_BEDROCK=1` is set.

   The wizard asks how you authenticate, asks for the region, checks which models your account can
   invoke, and writes the result into the `env` block of `~/.claude/settings.json`. It is the
   supported route and it replaces hand-editing that block.

4. **Pin the models.** (**user**) Without a pin, the `opus` and `sonnet` aliases resolve to Claude
   Code's built-in defaults, which can lag your account's enabled set. Pin explicitly:

   ```
   ANTHROPIC_DEFAULT_OPUS_MODEL     e.g. eu.anthropic.claude-opus-5
   ANTHROPIC_DEFAULT_SONNET_MODEL
   ANTHROPIC_DEFAULT_HAIKU_MODEL
   ```

   To keep the built-in defaults but change only the geography, set
   `ANTHROPIC_BEDROCK_REGION_PREFIX` instead — valid values `us`, `eu`, `apac`, `jp`, `au`, `global`.

   **`ANTHROPIC_SMALL_FAST_MODEL` is deprecated**; `ANTHROPIC_DEFAULT_HAIKU_MODEL` replaces it.

5. **Install the push gate**, per [`windows.md`](windows.md)'s *The pre-push gate*.

### Verify

`/status` inside a session shows the provider and the **resolved** region, and names the source when
the region came from your AWS config rather than `AWS_REGION`. Region resolution order is
`AWS_REGION`, then `AWS_DEFAULT_REGION`, then the active profile's `region`, then `us-east-1`.

Then confirm the `env` block survived the settings merge:

```
uv run python workstation/scripts/settings_delta.py --env
```

`env keys` must be non-empty and `CLAUDE_CODE_USE_BEDROCK` must not be `None`.

### Windows traps

- **Hardlinks are severed silently by any atomic-saving editor.** `CLAUDE.md` and `machine.md` are
  hardlinks, not junctions. [`windows.md`](windows.md) carries the detection command; run it after
  editing either file outside the repo.
- **`/logout` is unavailable on Bedrock** — authentication is AWS's, not Claude's.
- **The WebSearch tool is not available on Bedrock.**
- **Line endings.** `core.autocrlf=true` would break the `pre-push` hook with *bad interpreter*;
  [`../../../.gitattributes`](../../../.gitattributes) pins `pre-push` and `*.py` to LF for exactly
  this reason. Do not remove those rules.

---

## 3. Copilot on macOS

Two surfaces, configured separately: the VS Code extension and the `copilot` CLI. Set up whichever
you use.

### VS Code

Copilot has no config file of its own — everything is VS Code `settings.json`:

| Scope | Path |
|---|---|
| User | `$HOME/Library/Application Support/Code/User/settings.json` |
| Profile | `$HOME/Library/Application Support/Code/User/profiles/<profile ID>/settings.json` |
| Workspace | `.vscode/settings.json` |

To make Copilot read the same user instructions Claude reads, add: (**user**)

```jsonc
{
  "chat.useClaudeMdFile": true,                                    // reads ~/.claude/CLAUDE.md and CLAUDE.md
  "chat.useAgentsMdFile": true,                                    // reads AGENTS.md
  "github.copilot.chat.codeGeneration.useInstructionFiles": true   // reads .github/copilot-instructions.md
}
```

**All three default to on in VS Code 1.138.0** — `default:!0` in the build's own setting registrations,
read 2026-09-18. Set them anyway: an explicit value survives a default that changes between releases,
and the earlier record of this page read the first two as off on 1.137.0. With the first on, this
repo's [`../AGENT-INSTRUCTIONS.md`](../AGENT-INSTRUCTIONS.md) reaches Copilot through the same link
route 1 already created — no second file, no copy.

Related keys: `chat.instructionsFilesLocations` adds directories of `*.instructions.md`;
`chat.useCustomizationsInParentRepositories` walks up to parent repos.

### Skills

Same `SKILL.md` format as Claude, different parent directory:

```
~/.copilot/skills/<name>/SKILL.md      personal
.github/skills/<name>/SKILL.md         per project
.agents/skills/<name>/SKILL.md         per project
.claude/skills/<name>/SKILL.md         per project — read as-is
```

A project already carrying `.claude/skills/` needs nothing further. For the personal location, link
the global instructions and skills rather than copying them:

```sh
python workstation/scripts/link_config.py --agent copilot --apply   # python3 on macOS
```

That creates `~/.copilot/copilot-instructions.md` for the CLI, and `~/.agentic-workbench/machine.md`, the one
path the instructions name for machine state whichever agent reads them. For VS Code, also run the Claude link
route once so `~/.claude/CLAUDE.md` exists, then enable `chat.useClaudeMdFile`; Claude Code itself does
not need to be installed for that file to serve as VS Code's instruction source.

### The CLI

`copilot` stores configuration and state under `$HOME/.copilot`; `COPILOT_HOME` overrides the root.

| Path | Role |
|---|---|
| `~/.copilot/copilot-instructions.md` | user instructions loaded by Copilot CLI |
| `~/.copilot/settings.json` | **user settings — the file to edit** |
| `~/.copilot/config.json` | machine-managed; its own header says user settings belong in `settings.json` |
| `~/.copilot/mcp-config.json` | MCP servers |
| `~/.copilot/permissions-config.json` | tool and path permissions |
| `~/.copilot/instructions/`, `~/.copilot/prompts/` | user-level instructions and prompts |

Authentication is a GitHub token, resolved `COPILOT_GITHUB_TOKEN`, then `GH_TOKEN`, then
`GITHUB_TOKEN`; otherwise `copilot login`. (**user**)

`gh copilot` is a **launcher, not a separate tool** — it executes the `copilot` on your `PATH`, so it
has no configuration of its own. A legacy `gh-copilot` extension may still be installed and its
`~/.config/gh-copilot/config.yml` is then dead weight; `gh extension list` shows whether it is there.

The CLI also loads standalone skills from `~/.copilot/skills/`, as shown above, and that link is this
workbench's only route. Copilot's plugins (`copilot plugin --help`) are not used here.

### Verify

```sh
copilot --version
```

Then `/skills` in a `copilot` session should list the linked skills. In VS Code, open Chat and confirm the instruction file is listed among the context it loaded.

---

## 4. Copilot on Windows

Identical to route 3 except for the paths and one Windows-only setting.

### VS Code

| Scope | Path |
|---|---|
| User | `%APPDATA%\Code\User\settings.json` |
| Profile | `%APPDATA%\Code\User\profiles\<profile ID>\settings.json` |
| Workspace | `.vscode\settings.json` |

The settings themselves are the same: `chat.useClaudeMdFile`, `chat.useAgentsMdFile`,
`github.copilot.chat.codeGeneration.useInstructionFiles`,
`chat.instructionsFilesLocations`.

### The CLI

Same layout under `$HOME/.copilot`, same `COPILOT_HOME` override.

One setting exists only here — **`powershellFlags`**, the flags passed to `pwsh` on startup,
defaulting to `["-NoProfile", "-NoLogo"]`. Setting it replaces the defaults rather than adding to
them, and flags that change execution semantics (`-Command`, `-File`, `-NoExit`, `-NonInteractive`,
`-EncodedCommand`, `-InputFormat`, `-OutputFormat`) break the runtime. `copilot help config` carries
the full list.

If you also run Claude on this machine, note that `GH_HOST` is shared with the GitHub CLI;
`COPILOT_GH_HOST` overrides it for Copilot alone.

---

## How much of this was measured

The routes above mix observed fact with vendor documentation. Which is which:

| Claim | Status |
|---|---|
| macOS Claude link route, `link_config.py` behaviour, N of N linked | **observed** on the macOS workstation — the count moves as the `SKILLS`/hooks lists grow; see that machine's note under [`../../machines/`](../../machines/) for the count last measured there |
| Copilot CLI loads `~/.copilot/copilot-instructions.md` | **observed** — listed by Copilot CLI 1.0.85 under `/instructions` help |
| VS Code user settings path; `chat.useClaudeMdFile` / `useAgentsMdFile` exist | **observed** — VS Code 1.137.0, bundled `copilot-chat` 0.65.0 |
| `chat.useClaudeMdFile`, `chat.useAgentsMdFile`, `github.copilot.chat.codeGeneration.useInstructionFiles` default to on | **observed** — `default:!0` in the VS Code 1.138.0 build, 2026-09-18; that a Chat session then loads the files is not |
| Skills paths `.github/skills/`, `.agents/skills/`, `.claude/skills/` | **observed** — literal table in the VS Code 1.137.0 build |
| `~/.copilot/` layout, `COPILOT_HOME`, token precedence, `powershellFlags` | **observed** — `copilot help config`, `copilot help environment` on macOS |
| `gh copilot` is a launcher | **observed** — `gh copilot --help` |
| Windows link route, junctions and hardlinks | documented in [`windows.md`](windows.md), last measured on the Windows machine — see [`../../machines/README.md`](../../machines/README.md) |
| Bedrock steps, IAM actions, model pinning, region order | **vendor documentation**, not executed in this repo |
| Copilot CLI paths **on Windows** | **not measured** — the CLI states `$HOME/.copilot` and was verified on macOS only |
| The standalone CLI reads `~/.copilot/skills/` outside a plugin | **observed** on the macOS workstation, Copilot CLI 1.0.63, 2026-09-13 — `/skills` in a session listed the skills `link_config.py --agent copilot` had linked there; see [`../../machines/macos-workstation.md`](../../machines/macos-workstation.md#copilot-cli) |

Anything marked *not measured* or *unresolved* should be settled on the machine in question and
recorded in that machine's file under [`../../machines/`](../../machines/), not here — this file is a
route, and a route carries no machine state.
