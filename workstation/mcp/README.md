# Workstation MCP Index

Where to find guidance for the MCP servers listed under *Cross-cutting aspects → 2. Workstation tooling → MCP servers* in [`SOURCE_CATALOGUE.md`](../../SOURCE_CATALOGUE.md). The sibling of [`cli/README.md`](../cli/README.md), which covers the CLI tools.

**Scope: third-party servers this machine consumes.** A server *authored* in this workbench — the shared server that skills get refactored into — is project output and belongs with the project, not here. `workstation/` describes this machine, never an architecture.

## What each file is for

| File | Objective | Read it when | In git |
|---|---|---|---|
| `setup.md` | Get the server registered with a client and know what it exposes — the config, which integration route was chosen and why, how to confirm it connected, and the traps. | Before relying on the server, or when a fresh machine needs setting up. | yes |
| `reference.md` | The server's own documentation page, ingested verbatim. | `setup.md` did not cover what you need. | no |

**Two files, not three.** The CLI tools split install from quick start because *flags are invisible until you read the docs*. MCP tools are not: they arrive in the model's tool list with their own schemas and descriptions. A flag table here would only restate what the agent can already see, so the run-time half of the contract collapses into `setup.md`, which carries only what the schemas do **not** say — which route to pick, what the server does to your machine, and what fails silently.

## Servers

| Server | Product | Transport | Guidance |
|---|---|---|---|
| `drawio-mcp` | draw.io MCP tool server | stdio | [`drawio-mcp/`](drawio-mcp/) |
| `ado-remote-mcp` | Azure DevOps MCP Server (remote) | http | [`ado-remote-mcp/`](ado-remote-mcp/) |
| `databricks-<service>` | Databricks managed MCP services (Genie One, DBSQL, web search, sandbox) | http (Claude) · stdio bridge (Copilot) | [`databricks-mcp/`](databricks-mcp/) |

**The user registers; this folder records** — see [`AGENTS.md`](../../AGENTS.md#the-user-installs-the-agent-records). Whether a server is actually registered and connected on a given machine is that machine's state, recorded under [`../machines/`](../machines/), not here: a row can be fully documented and still not live on this machine.

## Config lives outside this repo — except the shared project scope

A CLI tool is reproducible from `install.md` because the command is the whole story. An MCP server is not: registering it usually writes into a client's own config — for Claude Code at **user** scope, `~/.claude.json`, which is **not** symlinked into [`../agent/`](../agent/) and therefore not tracked here. Same for Copilot CLI's `~/.copilot/mcp-config.json`.

**Project scope is the deliberate exception.** Both Claude Code (`-s project`) and Copilot CLI (workspace scope) read the *same* file, `<repo>/.mcp.json`, and its schema is identical for both — a `claude mcp add -s project` invocation and a hand-edited Copilot workspace config produce the same JSON shape. That file **is** tracked (`.mcp.json` is not gitignored here), which makes a server registration a repo change everyone gets, instead of something each person runs by hand.

This repo drives that file from [`.mcp.json`](.mcp.json) here — the catalog of every server this folder documents — via `workstation/scripts/link_config.py --mcp`:

- **Report** (`--mcp`, no `--apply`): compares the catalog against `<repo>/.mcp.json` and shows each server as `linked`, `missing`, or `diverged`.
- **Apply** (`--mcp --apply`): adds every `missing` catalog entry to `<repo>/.mcp.json`, creating the file if needed. A live-only server the catalog doesn't know about is left alone. A `diverged` entry — present, but with a different value than the catalog — is reported and **skipped**, the same reconciliation-not-overwrite rule this repo already applies to a diverged `CLAUDE.md`.

So `setup.md` is still the reproducibility record for anything the catalog can't safely carry (a per-tenant OAuth client ID, a PAT), but the plain, works-for-everyone part of a server's config belongs in [`.mcp.json`](.mcp.json), not repeated by hand in each `setup.md`.

## Pin the package, or know that you haven't

Most stdio servers are run with `npx -y <package>`, which resolves the **latest** version on every launch. That is an unpinned dependency that can change tool schemas or behaviour part-way through a piece of work.

The [version-currency rule](../cli/README.md#version-currency--raise-it-dont-fix-it) applies here with a twist: for CLI tools you find a stale install and report it; for `npx`-launched servers there is no install to be stale, so **record the version observed in `setup.md` and treat a behaviour change as the signal**. Pin with `@<version>` in the args if a server proves unstable — that is the user's call, not a housekeeping step.
