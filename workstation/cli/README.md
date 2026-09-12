# Workstation CLI Index

Where to find guidance for the CLI tools listed under *Cross-cutting aspects → 2. Workstation tooling → CLI tools* in [`SOURCE_CATALOGUE.md`](../../SOURCE_CATALOGUE.md). These tools ingest and process sources into this repo; they are never inputs to a generated artefact.

For the MCP servers in that section's other half, see [`../mcp/README.md`](../mcp/README.md). Same purpose, different file contract.

Each tool has a folder here at `<tool>/` holding three files with distinct jobs. Load only the one you need — that separation is the point of the split.

## What each file is for

| File | Objective | Read it when | In git |
|---|---|---|---|
| `install.md` | Get the tool onto a machine — the per-platform command, what a successful verification looks like, runtime dependencies, and install-time traps such as a renamed formula or a same-named package by a different author. Platform-specific, **never machine-specific**. | The command is missing, or a fresh machine needs setting up. Skip it entirely if the tool already runs. | yes |
| `quick_start.md` | Run the tool correctly the first time — the invocations this workbench actually uses, the subcommands and flags worth knowing, and the run-time traps that cause silent or misleading failures. | Before invoking a tool you have not used this session. **This is the default file to load.** | yes |
| `reference.md` | The tool's own documentation page, ingested verbatim. Complete, but long and unfiltered. | `quick_start.md` did not cover what you need and you want full detail. | no |

`install.md` and `quick_start.md` are hand-authored and deliberately short, so either can be read in full without crowding a session's context. `reference.md` is machine-written, never hand-edited, and gitignored like the rest of the corpus — it is rebuildable from the URL in the register.

**The user installs; these files record** — see [`CLAUDE.md`](../../CLAUDE.md#the-user-installs-the-agent-records). An entry means the route is known, not that the command runs here.

Each `install.md` carries a `| Platform | Command |` table, currently macOS and Windows. **Adding a
platform means adding a row to each of the twelve** — plus one `../claude/setup/<platform>.md` and one
file in [`../machines/`](../machines/). Do that when a machine of that platform exists, not in advance:
twelve guessed `apt` package names would be twelve unverified claims, and the *Do not cross ecosystems
by name* trap at the bottom of this page is exactly how guessing goes wrong.

Install routes — formula names, buckets, and npm/pipx channels — **are not dated here**, because they go stale one tool at a time: each `install.md` carries its own `verified` date in frontmatter, and that is the one to trust. [`INGESTION_GUIDE.md`](../../INGESTION_GUIDE.md) §6a defines how an install route is resolved and verified; these files are the result of applying it.

## Route here, state in `machines/`

**An `install.md` answers *how do I get this tool*. It never answers *is it here*.**

That second question is per-machine, and this repo runs on more than one machine, so a single-valued
field cannot answer it honestly. `install.md` therefore carries **no version number and no install
status** — not in frontmatter, not in prose. What it does carry is the *shape* of a successful
verification, which is the same everywhere: `pandoc --version` starts with `pandoc 3.x.y` on every box
that has it.

Per-machine truth lives in [`../machines/`](../machines/) and is **measured, not written**:

```
python workstation/scripts/inventory.py
```

That prints the inventory table for the machine you are on — command, status, version — distinguishing
`absent` from `blocked`, which matters because they call for different responses. Paste it into the
machine's file; do not hand-edit the table. See [`../machines/README.md`](../machines/README.md) for
the rule on which file a given fact belongs in.

## Version currency — raise it, don't fix it

**If you find the installed version is behind the project's latest release, tell the user and stop — do not upgrade it yourself.** An upgrade can change output format, CLI flags, or rendering behaviour part-way through a piece of work, and that is the user's call to make, not a housekeeping step.

Report it as three facts, because they are three different situations:

Report it as three facts, because they are three different situations:

| What you found | What it means |
|---|---|
| Installed version < packaged version | A stale local install. `brew upgrade <formula>`, `scoop update <pkg>`, `winget upgrade <id>` or `npm install -g <pkg>@latest` clears it, depending on the route in `install.md`. |
| Packaged version < project's latest release | The formula or npm package lags upstream. Nothing local will fix it. |
| Installed version = latest everywhere | Current; record the date you checked. |

Only the first is a version *hold*, and a hold is a legitimate choice — record one under *Workstation
configuration* in the tool's `install.md`, since choosing to sit on a version is a route decision. The
second is a packaging property worth noting inline. Blurring the two produces misinformation, which is
why they are separated here.

**A stale install is recorded, not fixed.** It is machine state, so it goes in that machine's file in
[`../machines/`](../machines/) with the upgrade command beside it, and waits for the user.

**The two platforms can sit on different major versions at once**, because brew and npm move
independently — `dbml-cli` has been observed doing exactly that. When output differs between machines
and the input is identical, compare the two inventories before suspecting the input.

## Tools

Each row is named by the **command you type**, which is often not the package name. The register in [`SOURCES.md`](../../SOURCES.md) and [`SOURCE_CATALOGUE.md`](../../SOURCE_CATALOGUE.md) lists these tools under their package names, and the folders below follow the register — where command and folder differ, this table is the mapping.

| Command | Product | Guidance |
|---|---|---|
| `playwright` | Playwright | [`playwright/`](playwright/) |
| `pandoc` | Pandoc | [`pandoc/`](pandoc/) |
| `docling` | Docling | [`docling/`](docling/) |
| `magick` | ImageMagick | [`magick/`](magick/) |
| `defuddle` | Defuddle | [`defuddle/`](defuddle/) |
| `tesseract` | Tesseract OCR | [`tesseract/`](tesseract/) |
| `sem` | Sem | [`sem-cli/`](sem-cli/) |
| `weasyprint` | WeasyPrint | [`weasyprint/`](weasyprint/) |
| `dbml2sql` / `sql2dbml` / `db2dbml` | DBML CLI | [`dbml-cli/`](dbml-cli/) |
| `plantuml` | PlantUML | [`plantuml-cli/`](plantuml-cli/) |
| `mmdc` | Mermaid CLI | [`mermaid-cli/`](mermaid-cli/) |
| `d2` | D2 | [`d2-cli/`](d2-cli/) |

## Do not cross ecosystems by name

This trap applies to every tool above, so it stays here rather than being repeated in each tool's folder.

A tool's name resolving on the *other* ecosystem's registry is not evidence the tool is published there. PyPI `mermaid-cli`, PyPI `dbml`, and npm `weasyprint` all resolve, but to unrelated third-party wrappers stalled at v0.1.x — not to the tools above. A low version number is a tell, not the test: `d2` is worse precisely because both impostors look healthy, PyPI `d2` being `okanakbulut/d2` at 0.8.1 and npm `d2` being DHIS2's JavaScript client library at 31.10.2, neither of which is Terrastruct's diagram language.

Match a registry entry's repository against the `SOURCES.md` URL before believing it. Otherwise use only the commands in each tool's `install.md`.
