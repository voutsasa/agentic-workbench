# Workstation

What this workbench **runs on**, as opposed to what it reads. `docs/` is the corpus; this tree describes the machine that processes it.

**Nothing here should reach a generated artefact.** A constitution or skill produced by this workbench describes an architecture; these files describe a particular set of laptops and their toolchain. Keeping that line is the whole reason the split exists.

## Subfolders

| Path | What it holds | Start at |
|---|---|---|
| [`cli/`](cli/) | The CLI toolchain that ingests and converts sources. One folder per tool, each with an authored `install.md` and `quick_start.md` plus an ingested `reference.md`. | [`cli/README.md`](cli/README.md) — the `command → product → folder` map, and the version-currency rule. |
| [`mcp/`](mcp/) | Third-party MCP servers registered with this machine's agent clients. One folder per server, each with an authored `setup.md` plus an ingested `reference.md`. | [`mcp/README.md`](mcp/README.md) — the server table, and why that contract is two files. |
| [`agent/`](agent/) | The coding agents' own configuration, **linked into `~/.claude/`** so it is versioned instead of scattered through a home directory. Shared by every machine, unmodified. | [`agent/README.md`](agent/README.md) — the contract, and what is deliberately left untracked. The four agent-and-platform routes are in [`agent/setup/README.md`](agent/setup/README.md). |
| [`machines/`](machines/) | One file per machine this workbench runs on: paths, shell, which tools actually run, what is broken. The only place machine-specific facts belong. | [`machines/README.md`](machines/README.md) — the index, and the test for which file a fact belongs in. |
| [`scripts/`](scripts/) | Scripts that maintain this tree — the inventory probe that generates a machine's tool table, and the link checker for `~/.claude`. | [`scripts/README.md`](scripts/README.md) |

`cli/` and `mcp/` are two halves of one register section — *Cross-cutting aspects → 2. Workstation tooling* in [`SOURCES.md`](../SOURCES.md). They are split because the file contract differs, not because the purpose does. [`INGESTION_GUIDE.md`](../INGESTION_GUIDE.md) §6 covers both: §6a for CLI tools, §6b for MCP servers.

## Three rules that apply across the tree

**The user installs; these files record** — see [`CLAUDE.md`](../CLAUDE.md#the-user-installs-the-agent-records). A recorded route means the route is *known*, not that the tool is live here.

**Split by lifetime, not by platform.** Three kinds of fact live in this tree and they expire at
different rates, so they live in different files:

| Kind | Lives in | Expires |
|---|---|---|
| **Policy** — how the agent should work | `agent/AGENT-INSTRUCTIONS.md` | never |
| **Route** — how to install or link something | `cli/<tool>/install.md`, `agent/setup/` | slowly, one tool at a time |
| **State** — what is present, what is broken | `machines/<id>.md` | constantly |

Putting all three in one file means the slowest-changing content gets edited at the rate of the
fastest. [`machines/README.md`](machines/README.md) carries the test: *would this still be true on the
other machine?*

**`agent/` is live configuration.** Editing `~/.claude/CLAUDE.md` or any of the `review`, `python-quality`, `verify-docs` and `fix-findings` skills writes into this directory through the link. Check `git status` before overwriting any of them, and if this directory is ever moved or renamed, **repoint the links** — otherwise every session silently loses its global instructions. On Windows the files are hardlinks, which any atomic-saving editor severs without warning; [`agent/setup/windows.md`](agent/setup/windows.md) has the detection command.

**`agent/settings.json` is the exception: merged by hand, never linked.** Claude Code writes to `~/.claude/settings.json` itself, and on a provider-bound machine it also carries an `env` block this repo deliberately does not hold, so no route here overwrites the live one. Which machines are provider-bound belongs in [`machines/`](machines/), not in this tree. [`agent/README.md`](agent/README.md#settings-are-merged-never-linked) has the procedure.

## What is tracked

The authored guidance: `install.md`, `quick_start.md`, `setup.md`, every `README.md`, all of `agent/`, all of `machines/`, and `scripts/`. **Not** the ingested pages — `cli/*/reference.md` and `mcp/*/reference.md` are gitignored like the rest of the corpus, and are rebuildable from the URLs in the register.
