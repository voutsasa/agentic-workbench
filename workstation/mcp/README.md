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

| Server | Product | Transport | Registered | Guidance |
|---|---|---|---|---|
| `drawio-mcp` | draw.io MCP tool server | stdio | pending user | [`drawio-mcp/`](drawio-mcp/) |

**The user registers; this folder records** — see [`CLAUDE.md`](../../CLAUDE.md#the-user-installs-the-agent-records). The *Registered* column tracks the gap: a row can be fully documented and still not live on this machine.

## Config lives outside this repo

A CLI tool is reproducible from `install.md` because the command is the whole story. An MCP server is not: registering it writes into a client's own config — for Claude Code at user scope, `~/.claude.json`, which is **not** symlinked into [`../agent/`](../agent/) and therefore not tracked here.

So `setup.md` is the reproducibility record, not a convenience. If it does not carry the exact registration command, the server cannot be rebuilt on a fresh machine from this repo.

## Pin the package, or know that you haven't

Most stdio servers are run with `npx -y <package>`, which resolves the **latest** version on every launch. That is an unpinned dependency that can change tool schemas or behaviour part-way through a piece of work.

The [version-currency rule](../cli/README.md#version-currency--raise-it-dont-fix-it) applies here with a twist: for CLI tools you find a stale install and report it; for `npx`-launched servers there is no install to be stale, so **record the version observed in `setup.md` and treat a behaviour change as the signal**. Pin with `@<version>` in the args if a server proves unstable — that is the user's call, not a housekeeping step.
