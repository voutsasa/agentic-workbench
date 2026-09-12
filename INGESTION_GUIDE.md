---
role: Routing and process guide for pulling a source into local storage
updated: 2026-09-04
verified: never
---

# Ingestion Guide

How to pull each source in `SOURCES.md` into this workbench as clean, reviewable local markdown, before it's distilled into constitutions/skills.

## 1. Classify the source, then route it

```
Is it a github.com/<owner>/<repo> URL?
  └── YES → fetch the raw README only. Do NOT clone.
             curl -s https://raw.githubusercontent.com/<owner>/<repo>/<branch>/README.md
             save → docs/web/<topic name>.md

Is it a direct file (.pdf)?
  └── YES → download the file itself, don't scrape a rendered viewer.
             curl -s -o "docs/web/<topic name>.pdf" <url>

Is it a Docusaurus site (its theme class names show up in the raw HTML —
theme-doc-markdown, docMainContainer_ — confirmed on playwright.dev,
dbml.dbdiagram.io, d2lang.com, drawio.com)?
  └── YES → curl the raw HTML, extract the article node, convert with
             pandoc. Do NOT use WebFetch here — verified 2026-09-04,
             WebFetch paraphrases the source text through its own small
             model even under an explicit "verbatim, do not summarize"
             instruction (the real text "is an end-to-end test
             framework" came back as "serves as an end-to-end testing
             framework"), which fails the quality check in §3 below.
             curl -sL -A "Mozilla/5.0" <url> -o <tmp>/page.html
             python extract_docusaurus_article.py <tmp>/page.html \
               div.theme-doc-markdown | pandoc -f html -t gfm \
               -o docs/web/<topic name>.md
             extract_docusaurus_article.py (repo root, stdlib-only) pulls
             one HTML node by `tag.class` or `tag#id` and strips the
             tags pandoc's gfm writer can't map cleanly — div, header,
             span, inline <svg>, base64 icon <img>s, <style>, bookmark
             <a name>s — so the source's own text survives untouched.
             A non-Docusaurus custom layout can reuse it with a
             different selector: plantuml.com's article sits in
             `<main id="D7">`, so `main#D7` finds it there instead.

Is it a plain server-rendered doc/blog (Sphinx, ReadTheDocs, MkDocs,
VitePress, mdBook, static HTML, classic blogs)?
  └── YES → WebFetch directly.
             save → docs/web/<topic name>.md
             Caveat, verified on Docusaurus (2026-09-04): WebFetch's own
             description says it processes content through "a small,
             fast model", which can paraphrase rather than scrape even
             when told not to. Spot-check a paragraph against the raw
             HTML before trusting the output; not yet checked one way
             or the other on Sphinx/ReadTheDocs/MkDocs/mdBook, so this
             is a caveat to verify per source, not a blanket ban.

Is it a JS-hydrated doc platform (Mintlify, Fern, Rspress-style —
anything that returned raw component/JSX source under WebFetch, as
agentskills.io did)?
  └── YES → render with Playwright (headless — no browser extension
             involved) then extract with defuddle, convert with
             pandoc if needed.
             save → docs/web/<topic name>.md
```

## 2. Where things land

```
docs/web/<topic name>.{md,pdf}
```

One flat directory — no per-section subfolders, and no folders per architecture layer. Layer grouping lives in `SOURCES.md` only, because a source can feed more than one layer and physical folders would force a false single home.

**One exception: workstation tooling.** Entries under *Cross-cutting aspects → 2. Workstation tooling* land beside their authored guidance instead, in one of two trees depending on the subsection the entry sits in. See §6.

```
#### CLI tools    → workstation/cli/<topic name>/reference.md
#### MCP servers  → workstation/mcp/<topic name>/reference.md
```

`<topic name>` is the exact link text between the `[ ]` in `SOURCES.md` (e.g. `[Pydantic AI](...)` → `docs/web/Pydantic AI.md`). GitHub sources use the link text too, not the repo name, so the file matches whatever `SOURCES.md` calls it.

**Filename sanitization:** a `: ` in the title — the colon together with the space that follows it — is written as ` - ` in the filename, so the result has single spaces around the dash and not a doubled one — `[Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl]` → `Understanding Spec-Driven-Development - Kiro, spec-kit, and Tessl.md`. This is the only permitted deviation from exact link text.

## 3. Quality check before treating a file as "ingested"

- Headings and lists survived structurally (not flattened into one paragraph).
- Tables are still tables, not scrambled into run-on text — the usual failure mode for docling/pandoc on complex layouts.
- No leftover markup noise: nav bars, cookie banners, JSX/React source, "Edit this page" links.
  For a Docusaurus extraction, `grep -c "<div\|<header\|<span\|<svg\|<style" out.md` should be 0 —
  any hit is a tag pandoc's gfm writer couldn't map and fell back to raw HTML for, which is the
  same failure mode as the base64-icon and hash-link cases `extract_docusaurus_article.py` exists
  to strip.
- For PDFs converted to text: spot-check page breaks didn't split sentences or merge columns.
- **For a `.docx` with diagrams: count the figures.** docling drops every DrawingML figure at exit 0 when LibreOffice is unreachable, so headings and tables pass this check while the images are gone. `(Select-String -Path out.md -Pattern "data:image/[a-z]+;base64" -AllMatches).Matches.Count` against the source's figure count settles it; the opt-in is in [`workstation/cli/docling/quick_start.md`](workstation/cli/docling/quick_start.md#figures-in-a-docx-need-libreoffice-or-they-vanish-silently).

Any file that fails this check gets re-run through the JS-hydrated path (render + defuddle) even if it was first attempted as a plain fetch, or flagged for manual review if both fail.

## 4. Post-processing: embedded images

Conversions from PDF or `.docx` (docling, pandoc) often inline images as base64 data URIs, which bloats the file and makes it unreadable. Run `clean_md_images.py` to extract them:

```
python clean_md_images.py "docs/web/<topic name>.md"
```

It writes `<topic name>-no-base64.md` alongside the original and drops the PNGs into a sibling `<topic name>/` folder. Replace the original with the cleaned file once you've checked it.

## 5. After ingestion

Add the source's one-line (≤20 words) capability summary to [`SOURCE_CATALOGUE.md`](SOURCE_CATALOGUE.md), in the same section and position it occupies in `SOURCES.md`. The two files must stay entry-for-entry identical. `README.md` is the landing page and carries no source entries, so it needs no change.

## 6. Workstation tooling entries: also record how it is set up

Applies **only** to entries under *Cross-cutting aspects → 2. Workstation tooling*. Every other entry stops at step 5 — setup instructions are meaningless for a book, a blog post, or a framework's docs.

These entries are tools someone has to actually set up and then run, so the capability summary alone doesn't make the register reproducible on a fresh machine. That detail goes in the tool's own folder, not in `SOURCE_CATALOGUE.md` — the catalogue keeps one line per source so it stays entry-for-entry identical to `SOURCES.md`.

**The user installs and registers; the agent records** — see [`CLAUDE.md`](CLAUDE.md#the-user-installs-the-agent-records). The consequence for this section: a folder written before the user has run the command documents an **intended** setup, not an observed one. Say which it is — an unverified version string is worse than an absent one.

Which route applies depends on the subsection the entry sits in: `#### CLI tools` in §6a, `#### MCP servers` in §6b.

### 6a. CLI tools

Create `workstation/cli/<tool>/` and write three files:

```
install.md      authored — how to get it onto a machine
quick_start.md  authored — how to run it correctly the first time
reference.md    the ingested page, per §1 routing
```

Then add a row to the tools table in [`workstation/cli/README.md`](workstation/cli/README.md), in the same position the tool occupies in `SOURCES.md`, keyed by **the command you type** rather than the package name:

```
| `<command>` | <Product> | [`<tool>/`](<tool>/) |
```

The index sits inside `workstation/cli/` alongside the tool folders, so the link target is a bare `<tool>/`. Its MCP counterpart at `workstation/mcp/README.md` follows the same pattern.

#### What goes in each file

**`install.md`** — the macOS and Windows commands as a two-row table, a `--version` line with the value you actually observed and the date, any runtime dependency the package does not pull in, and install-time traps: a renamed formula, a differently named binary, a missing package on one platform. Keep it skippable — someone whose tool already runs should not need to read it.

**`quick_start.md`** — a one-line statement of what the tool is for and when to prefer it over the obvious alternative, the invocations this workbench actually uses, a capability or flag table, and the run-time traps that produce silent or misleading failures. This is the file an agent loads before invoking a tool it has not used this session, so it has to be worth its context: prefer the trap that costs an hour over the flag that is easy to look up.

**Verify both against the installed tool.** Run `--help`, `--version`, and the failure case itself rather than copying a claim forward. An assertion that a route is broken is worth recording only if you have seen it break.

Traps that apply to every tool — the cross-ecosystem impostor problem in particular — stay in `workstation/cli/README.md` rather than being repeated in each tool's folder.

#### Resolving the two commands

Preferred managers are **brew** on macOS and **scoop** on Windows. Fall back only when the package genuinely isn't there:

```
1. brew (macOS) / scoop (Windows)
2. the tool's own ecosystem
     Node-based    → npm    `npm install -g <pkg>`
     Python-based  → pipx   `pipx install <pkg>`
3. neither → record the project's own documented method verbatim
```

**Step 2 is a branch, not a ranking.** npm and pipx are never ranked against each other and you never "fall through" from one to the other: a tool is published to the ecosystem it is written in, and the other ecosystem either has nothing or has something that isn't this tool (see the cross-ecosystem trap below). Choose by implementation language and take that project's canonical channel.

In the rare case where the maintainers genuinely publish to both, prefer **the ecosystem the tool will be driven from in practice** — you want the API you'll be writing against, not merely a working binary. Version parity is a tiebreak only after that, and a lagging binding is an acceptable cost. Playwright is the current example: it is published to both, npm 1.62.0 against PyPI 1.61.0, and it is taken from PyPI because this workbench scripts it in Python.

#### Verify, never assume

These checks cover the **install channel** — is this package the real tool? The **source URL** itself is governed separately by the *First-party sources only* convention in [`SOURCES.md`](SOURCES.md), applied when the entry is added rather than when the tool is installed. The two are complementary: an entry can point at the project's genuine docs site and still list an impostor package, or vice versa.

A plausible-looking formula name is not evidence the package exists. Check each one:

```
brew   brew info --formula <name>          # non-zero / empty output = absent
scoop  curl -s -o /dev/null -w "%{http_code}" \
         https://raw.githubusercontent.com/ScoopInstaller/Main/master/bucket/<name>.json
       # 404 → retry against .../ScoopInstaller/Extras/...; record the bucket that hit
npm    curl -s https://registry.npmjs.org/<pkg>       # scoped: / becomes %2f
pipx   curl -s -o /dev/null -w "%{http_code}" https://pypi.org/pypi/<pkg>/json
```

Record the bucket in the scoop command (`scoop install extras/plantuml`) so the reader doesn't have to guess which bucket to add.

#### Four failure modes to check for

- **Cross-ecosystem impostor.** The tool's name existing on the *other* ecosystem's registry is not evidence the tool is published there. It is usually an unrelated third party's wrapper or port, stalled at v0.1.x — PyPI `mermaid-cli` is `seigok/mermaid-cli-python`, PyPI `dbml` is a SQLAlchemy converter, npm `weasyprint` is a Node shell-out around the real Python tool. A low version number is a tell, not the test: PyPI `d2` (0.8.1) and npm `d2` (31.10.2) are both actively maintained, and neither is Terrastruct's diagram language. Match the registry entry's repository against the `SOURCES.md` URL before believing it. This is the reason step 2 branches on language instead of ranking npm above pipx.
- **Name collision.** The obvious name can be a different tool. `brew install sem` installs `schema-evolution-manager`, not the semantic-diff `sem` — the correct formula is `sem-cli`. Confirm the manifest's homepage points at the same project as the `SOURCES.md` URL before recording it.
- **Version lag.** A formula can trail the project's own channel by a major version. Where the gap is a major version, note it inline: `` `brew install <formula>` (8.3.1, lags npm 9.x) ``. A recorded gap is a snapshot, not a property of the tool — `dbml-cli` carried exactly that annotation until brew caught up to 9.x on 31 July 2026, at which point the note became misinformation. Re-verify inline version claims whenever you revisit a tool's `install.md`, and delete the ones that have closed. As of 1 August 2026 no *packaged route* lags — every formula matches its project's own latest release.

Whether a **package** lags upstream and whether **this workstation** is behind its package are different problems with different fixes; `dbml-cli` was the worked example of the second, at 8.3.1 against 9.0.0 stable until it was upgraded to 9.1.1 on 1 August 2026. A stale local install is never fixed by changing the recorded install route. [`workstation/cli/README.md`](workstation/cli/README.md) sets out how to report each case — and note that finding one is a matter to raise with the user, not to quietly upgrade.
- **Unstated runtime dependency.** The package alone may not be a working install — `plantuml` needs Java and Graphviz. Append them: `` `brew install plantuml` (needs `openjdk`, `graphviz`) ``.

#### Links

**Install docs** is required — the project's own installation page, not a distro's. **Quick start** is conditional: include it only when it is a *separate* page from the install docs. For most tools install and first use are one page, and repeating that URL twice adds nothing; write `—` in the quick-start cell instead.

### 6b. MCP servers

For entries under `#### MCP servers`. Create `workstation/mcp/<server>/` and write **two** files:

```
setup.md        authored — how to register it and what it exposes
reference.md    the ingested page, per §1 routing
```

Then add a row to the servers table in [`workstation/mcp/README.md`](workstation/mcp/README.md), in the same position the server occupies in `SOURCES.md`:

```
| `<server>` | <Product> | <transport> | [`<server>/`](<server>/) |
```

**Two files, not three** — the reasoning lives in [`workstation/mcp/README.md`](workstation/mcp/README.md). In short: `setup.md` carries only what the tool schemas do not.

**§6a's packaging checks do not apply here.** No brew formula, no scoop bucket, no npm-vs-pipx branch — an MCP server is registered with a client, not installed onto a PATH. What carries over is the principle behind them: confirm the package's repository matches the `SOURCES.md` URL before believing it is the real thing.

**`setup.md`** — what the server is and its transport, the observed version and date, which route was chosen when the vendor offers several, the exact registration command with its scope, how to confirm it connected, the tool names, and the traps. Note explicitly where the config was written, because for user-scope servers that file sits outside this repo and the command is the only reproducibility record.

**What can be verified without registering.** `--version` and `--help` run against the package directly, so the version, transport, and flags are observable before anything touches a client's config. The connection is not: `claude mcp list` only reports once the user has run the registration. Record the first group as observed, and mark the connection as pending until they confirm it.

An unpinned `npx -y` launcher resolves latest on every run, so even an observed version is a snapshot rather than a guarantee — say so where you record it.

## Scope

This guide covers every `[bracket link]` entry in `SOURCES.md`. All of them are external — each carries an `http(s)` URL — so nothing in the register is out of scope here. The only thing that varies is the destination: workstation tooling entries land in the two `workstation/` trees per §2 and §6, everything else in `docs/web/`.
