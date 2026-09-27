# Workstation tooling entries

Applies **only** to entries under *Cross-cutting aspects → 2. Workstation tooling* in `SOURCES.md`.
Every other entry stops at the skill's §3.

These entries are tools someone has to set up and then run, so a capability summary alone does not make
the register reproducible on a fresh machine. That detail goes in the tool's own folder, never in
`SOURCE_CATALOGUE.md` — the catalogue keeps one line per source so it stays entry-for-entry identical
to `SOURCES.md`.

## The rule that governs everything below

**The user installs and registers; the agent records.** Resolving the route, checking the package is
genuine, and writing it down is the agent's work. Running `brew install`, `claude mcp add`, or an
upgrade is not: it changes the user's machine, and a tool that shifts version mid-task breaks the work
in progress. Hand over the exact command and wait.

The consequence for this file: **a folder written before the user has run the command documents an
*intended* setup, not an observed one.** Say which it is. An unverified version string is worse than an
absent one.

Which route applies depends on the subsection the entry sits under.

---

## A. CLI tools (`#### CLI tools`)

Create `workstation/cli/<tool>/` and write three files:

| File | Authored? | Contents |
|---|---|---|
| `install.md` | authored | how to get it onto a machine |
| `quick_start.md` | authored | how to run it correctly the first time |
| `reference.md` | ingested, via `fetch-to-markdown` | the tool's own docs page |

Then add a row to the tools table in `workstation/cli/README.md`, **in the same position the tool
occupies in `SOURCES.md`**, keyed by *the command you type* rather than the package name:

```
| `<command>` | <Product> | [`<tool>/`](<tool>/) |
```

The index sits inside `workstation/cli/` alongside the tool folders, so the link target is a bare
`<tool>/`.

### What goes in each file

**`install.md`** — the macOS and Windows commands as a two-row table; the `--version` command and the
*shape* of its output (**not the value you observed** — that is install status and belongs in
`workstation/machines/<id>.md`); any runtime dependency the package does not pull in; and install-time
traps: a renamed formula, a differently named binary, a package missing on one platform. Keep it
skippable — someone whose tool already runs should not need to read it.

**`quick_start.md`** — one line on what the tool is for and when to prefer it over the obvious
alternative; the invocations this workbench actually uses; a capability or flag table; and the run-time
traps that produce **silent or misleading** failures. This is the file an agent loads before invoking a
tool it has not used this session, so it has to be worth its context: **prefer the trap that costs an
hour over the flag that is easy to look up.**

**Verify both against the installed tool.** Run `--help`, `--version`, and the failure case itself
rather than copying a claim forward. An assertion that a route is broken is worth recording only if you
have seen it break.

Traps that apply to every tool — the cross-ecosystem impostor problem in particular — stay in
`workstation/cli/README.md` rather than being repeated per folder.

### Resolving the two commands

Preferred managers are **brew** on macOS and **scoop** on Windows. Fall back only when the package
genuinely is not there:

```
1. brew (macOS) / scoop (Windows)
2. the tool's own ecosystem
     Node-based    → npm    `npm install -g <pkg>`
     Python-based  → uv     `uv tool install --python 3.12 <pkg>`
                     pipx   `pipx install <pkg>`, only where install.md records why uv cannot work
3. neither → record the project's own documented method verbatim
```

**Within Python, uv comes before pipx.** Both install the same package from the same index, so this is
a ranking of installers, not of ecosystems. `uv` is already a required prerequisite
(`workstation/dependencies.toml`) and pipx is not. `--python 3.12` is pinned because uv otherwise
picks whatever interpreter it finds first (3.11.15 on macOS, 2026-09-27). A tool that needs system
libraries (WeasyPrint needs Pango and GObject) belongs on brew or scoop, which bundle them.
`uv tool install weasyprint` installs cleanly and then fails at import.

**Step 2 is a branch, not a ranking.** npm and pipx are never ranked against each other and you never
fall through from one to the other: a tool is published to the ecosystem it is written in, and the
other ecosystem either has nothing or has something that is not this tool. Choose by implementation
language and take that project's canonical channel.

Where maintainers genuinely publish to both, prefer **the ecosystem the tool will be driven from in
practice** — you want the API you will be writing against, not merely a working binary. Version parity
is a tiebreak only after that, and a lagging binding is an acceptable cost. Playwright is the worked
example: published to both, npm 1.62.0 against PyPI 1.61.0, taken from PyPI because this workbench
scripts it in Python.

### Verify the package, never assume it

These checks cover the **install channel** — is this package the real tool? The **source URL** is
governed separately by the *First-party sources only* convention in `SOURCES.md`, applied when the
entry is added rather than when the tool is installed. The two are complementary: an entry can point at
the project's genuine docs site and still list an impostor package, or the reverse.

A plausible-looking formula name is not evidence the package exists. Check each one:

```sh
# brew
brew info --formula <name>                 # non-zero / empty output = absent

# scoop
curl -s -o /dev/null -w "%{http_code}" \
  https://raw.githubusercontent.com/ScoopInstaller/Main/master/bucket/<name>.json
# 404 → retry against .../ScoopInstaller/Extras/...; record the bucket that hit

# npm
curl -s https://registry.npmjs.org/<pkg>    # scoped: / becomes %2f

# PyPI (uv tool, or pipx as the fallback)
curl -s -o /dev/null -w "%{http_code}" https://pypi.org/pypi/<pkg>/json
```

Record the bucket in the scoop command (`scoop install extras/plantuml`) so the reader does not have to
guess which bucket to add.

### Four failure modes to check for

| Mode | What it looks like | The test |
|---|---|---|
| **Cross-ecosystem impostor** | The name exists on the *other* ecosystem's registry, but it is a third party's wrapper or port — PyPI `mermaid-cli` is `seigok/mermaid-cli-python`, PyPI `dbml` is a SQLAlchemy converter, npm `weasyprint` is a Node shell-out around the real Python tool | Match the registry entry's **repository** against the `SOURCES.md` URL. A low version number is a tell, not the test: PyPI `d2` (0.8.1) and npm `d2` (31.10.2) are both actively maintained and neither is Terrastruct's diagram language. This is why step 2 branches on implementation language instead of ranking npm above pipx |
| **Name collision** | The obvious name is a different tool — `brew install sem` installs `schema-evolution-manager`, not the semantic-diff `sem`; the correct formula is `sem-cli` | Confirm the manifest's **homepage** points at the same project as the `SOURCES.md` URL |
| **Version lag** | A formula trails the project's own channel by a major version | Say *that a lag is possible and which channel leads* — **never the two numbers.** A recorded gap is a snapshot that becomes misinformation the moment the channel catches up; `dbml-cli` carried exactly such a note until brew caught up on 31 July 2026, at which point it was simply wrong |
| **Unstated runtime dependency** | The package alone is not a working install — `plantuml` needs Java and Graphviz | Append them: `` `brew install plantuml` (needs `openjdk`, `graphviz`) `` |

**Two different problems, two different fixes.** Whether a *package* lags upstream and whether *this
workstation* is behind its package are not the same thing. `dbml-cli` was the worked example of the
second, at 8.3.1 against 9.0.0 stable until it was upgraded to 9.1.1 on 1 August 2026. **A stale local
install is never fixed by changing the recorded install route**, and whether a given machine is behind
is install status belonging in `workstation/machines/<id>.md`. `workstation/cli/README.md` sets out how
to report each case — and finding one is a matter to raise with the user, not to quietly upgrade.

### Links in the row

**Install docs** is required — the project's own installation page, not a distro's. **Quick start** is
conditional: include it only when it is a *separate* page from the install docs. For most tools the two
are one page and repeating the URL adds nothing; write `—` in the quick-start cell instead.

---

## B. MCP servers (`#### MCP servers`)

Create `workstation/mcp/<server>/` and write **two** files:

| File | Authored? | Contents |
|---|---|---|
| `setup.md` | authored | how to register it and what it exposes |
| `reference.md` | ingested, via `fetch-to-markdown` | the server's own docs page |

Then add a row to the servers table in `workstation/mcp/README.md`, in the same position the server
occupies in `SOURCES.md`:

```
| `<server>` | <Product> | <transport> | [`<server>/`](<server>/) |
```

**Two files, not three**, and the reasoning lives in `workstation/mcp/README.md`: `setup.md` carries
only what the tool schemas do not.

**Section A's packaging checks do not apply here.** No brew formula, no scoop bucket, no npm-vs-pipx
branch — an MCP server is registered with a client, not installed onto a PATH. What carries over is the
principle behind them: confirm the package's repository matches the `SOURCES.md` URL before believing
it is the real thing.

**`setup.md`** — what the server is and its transport; the observed version and date; which route was
chosen where the vendor offers several; the exact registration command **with its scope**; how to
confirm it connected; the tool names; and the traps. Note explicitly **where the config was written**,
because for a user-scope server that file sits outside this repo and the command is the only
reproducibility record.

### What can be verified without registering

`--version` and `--help` run against the package directly, so **the version, transport and flags are
observable before anything touches a client's config.** The connection is not: `claude mcp list` only
reports once the user has run the registration.

Record the first group as observed. Mark the connection **pending** until the user confirms it.

An unpinned `npx -y` launcher resolves latest on every run, so even an observed version is a snapshot
rather than a guarantee — say so where you record it.
