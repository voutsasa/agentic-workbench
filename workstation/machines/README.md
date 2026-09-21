# Machines

Each machine has a Markdown state note and a TOML readiness profile. The note records **state**: what
is true of that box right now. Common requirements live in [`../dependencies.toml`](../dependencies.toml);
the `<machine>.prerequisites.toml` companion overrides only what differs on that box, such as command
names, version floors, or its chosen package manager.

## Why this folder exists

`workstation/` used to mix three kinds of fact with three different lifetimes, which is why
`agent/AGENT-INSTRUCTIONS.md` — a file every machine shares unmodified — ended up carrying a Windows-only
`## Environment` section, and why each `install.md` carried a `status:` field it could not honestly
answer. The split is by **lifetime**, not by platform:

| Kind | Lives in | Scope | Goes stale |
|---|---|---|---|
| **Policy** — how the agent should work | [`../agent/AGENT-INSTRUCTIONS.md`](../agent/AGENT-INSTRUCTIONS.md) | every machine, every platform | no |
| **Route** — how to install or link something | [`../cli/<tool>/install.md`](../cli/), [`../agent/setup/`](../agent/setup/) | per platform, machine-independent | slowly, one tool at a time |
| **Common readiness** — shared dependencies, defaults, corrective text | [`../dependencies.toml`](../dependencies.toml) | every machine | when shared requirements change |
| **Machine readiness overrides** — command names, version floors, package-manager choice | **`<machine>.prerequisites.toml` here** | one box | when that machine's requirements differ |
| **State** — what is present, and what is broken | **`<machine>.md` here** | one box | constantly |

The test for which file a fact belongs in: *would this still be true on the other machine?* If yes it
is policy or route. If no it belongs here.

A fact in the wrong file gets edited at the wrong rate — the slowest-changing content at the rate of
the fastest. That is why `AGENT-INSTRUCTIONS.md` names no platform, why `install.md` carries no current
version or install status (a version survives there only as evidence for a trap, which cannot go
stale), and why a machine's tool table is measured by `../scripts/inventory.py` rather than written.

## Files

| Machine | Prerequisites | Platform | Repo path | Inventory verified |
|---|---|---|---|---|
| [`windows-ema-pf5n4xe7.md`](windows-ema-pf5n4xe7.md) | [`windows-ema-pf5n4xe7.prerequisites.toml`](windows-ema-pf5n4xe7.prerequisites.toml) | Windows 11 (build 26200) | `C:\Users\voutsas\Work\Development\agentic-coding\agentic-workbench` | 21 September 2026 |
| [`macos-workstation.md`](macos-workstation.md) | [`macos-workstation.prerequisites.toml`](macos-workstation.prerequisites.toml) | macOS 26.6.2 (arm64) | `~/Development/agentic-coding/agentic-workbench` | 18 September 2026 |

The filename is `<platform>-<id>.md`, lowercased. The id is usually the hostname —
`workstation/scripts/inventory.py --json` prints that form under `suggested_id` — but it does
not have to be: this repo is pushed to a shared remote, and a hostname is often a person's name.
`macos-workstation.md` is named for the role instead, and `inventory.py --host <label>` keeps the DNS
name out of the table it generates.

Nothing depends on the filename matching the hostname. `link_config.py` takes `--machine <id>`, and
without it falls back to the only file for the platform.

## Adding a machine

1. Clone the repo. Note where — the path is per-machine and belongs in the new file, nowhere else.
2. Run `<python> workstation/scripts/inventory.py --host <id>` — `<python>` being the repo's `.venv`
   interpreter when it exists, otherwise the bootstrap one: `python3` on macOS, `python` on Windows
   ([`../scripts/README.md`](../scripts/README.md)). Paste the table into the *CLI toolchain* section. Do not hand-write that table; the
   point of the script is that the count is measured.
3. Record the shell, the path, and anything that behaves unexpectedly. Blockers are the highest-value
   content here — a tool that is absent costs one install, a tool that fails *silently* costs a
   session.
4. Add a row to the table above.
5. Add `<machine>.prerequisites.toml`, recording only values that differ from
   [`../dependencies.toml`](../dependencies.toml), normally Python's command and the platform package
   manager. Any shared dependency uses `provisioning = "external"`; this workbench detects it but
   does not provide its installation route.
6. Run `<python> workstation/scripts/status.py --machine <id>` and resolve required failures.
7. Follow the matching [`../agent/setup/`](../agent/setup/) file to put the config in place.

A new **platform** additionally needs one `setup/<platform>.md` and a third row in each
`install.md` platform table. Write those when a machine exists — a dozen guessed `apt` package names
would be a dozen unverified claims, which is worse than an absent row.

## How the agent reads this

Nothing here is loaded automatically. [`../agent/AGENT-INSTRUCTIONS.md`](../agent/AGENT-INSTRUCTIONS.md) tells
the agent to read `~/.claude/machine.md`, which is a path that is **identical on every
machine while its content differs** — that indirection is what lets the shared file point at
per-machine truth without naming a platform.

Before the machine note is linked, an agent working in this repo should read the relevant file here
directly. Its state is recorded in each machine file's *Claude Code config* or *Not yet installed*
section; link it through the matching setup route when it is absent.
