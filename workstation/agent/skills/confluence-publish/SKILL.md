---
name: confluence-publish
description: Publish Markdown from this repository to a Confluence Cloud page, under a target page you name. Use whenever the user asks to publish, push, upload or sync a document or a directory to Confluence. Takes the target page's URL and the source path, declares the space if it is new, and handles the page hierarchy, the local conversion check, the renderer requirements and the delete-before-republish rule. Not for retrieving pages from Confluence — that is confluence-export.
author: Achilleas Voutsas
version: 0.4.0
---

# Publishing Markdown to Confluence

One direction only: Markdown here becomes a page there. `confluence-content/spaces/*/publish/` is
the source and Confluence is a copy of it.

**Which `confluence-sync-md` runs.** Every command below is `uv run --no-sync -- confluence-sync-md`: in a
repository that pins the tool (`uv add`), that is the pinned copy in its `.venv`; anywhere else it is
the global install from `workstation/cli/confluence-sync-md/install.md`. `--no-sync` keeps it from
installing or updating anything in the repository, and `--` ends uv's own options.

If that command fails to spawn with `Access is denied`, that is a Windows Defender/EDR quarantine,
not a credentials problem — see
[confluence-export's note](../confluence-export/SKILL.md#if-the-exe-fails-to-spawn-with-access-is-denied)
for the `python -m` substitute.

## The two inputs

Every publish needs both. **Ask for whichever is missing — never infer either.**

| Input | What to ask for | Why it cannot be guessed |
|---|---|---|
| **Target page** | the URL of the Confluence page the content will hang beneath, copied from the browser | Without it md2conf puts everything under the *space home page*. The URL also carries the space, and a page in the wrong space silently relocates the entire publish |
| **Source** | the file, or the directory, to publish | A directory publish has a different blast radius, and md2conf will walk a whole tree |

The target page URL looks like this — everything the publish needs is in it:

```
https://euema.atlassian.net/wiki/spaces/BIAD/pages/7314209/Solution+Architecture
                                        ^^^^ space key        ^^^^^^^ page ID
```

A space *overview* URL is not a target page: it has no `/pages/<id>/`. If the user gives one, ask
which page inside that space the content belongs under — or confirm they really mean the space home
page, which is what omitting the target does.

For the source, confirm **which** directory when it is a directory. It must be a space's `publish/`
directory or something below it: a run rooted at `confluence-content/` or at `spaces/` sweeps every
space into one page tree, because md2conf mirrors directory structure and knows nothing about this
repository's layout.

## Where the commands act
Commands act on a **content root** — the directory holding `spaces/`, which in this repository is
`confluence-content/` itself, not the directory above it. `--content-root ~/docs` therefore means
`~/docs/spaces/<Space>/`. It is an input, not something the tool infers about itself, so one
installation serves any number of trees: `--content-root DIR`, else `$CONFLUENCE_CONTENT_ROOT`,
else the nearest `confluence-content/` at or above the working directory. Running from inside this
repository needs none of them — `capabilities --json` reports the root it resolved.

## Then: is the space set up?

The source has to live under the space that the target page is in. Run this with the target page's
URL — it reports the space directory if it exists and creates it if it does not:

```sh
source .env && uv run --no-sync -- confluence-sync-md space declare <target-page-url>
```

It prints where publish sources belong for that space. It never overwrites an existing
`space_key.json`, and it fetches the space's *name* — which the directory is named after — from the
API, so it needs a sourced `.env` the first time a space is seen.

**If the user's documents are not under that `publish/` directory, stop and say where they must go.**
Do not move or copy them without asking: which documents belong in the repository is the user's
call, not a side effect of a publish.

## Then: how the documents are organised

This decides the page tree, and it is decided by **filenames**, not by flags.

A directory becomes a *page with children* when it contains one of these. **md2conf checks them in
this order and takes the first it finds** (`processor.py:305-310`) — which is not the order to
recommend authoring them in:

| Checked | File in the directory | |
|---|---|---|
| 1st | `index.md` | works |
| 2nd | `README.md` | works — **and silently outranks the next row** |
| 3rd | `<dirname>.md` — e.g. `solution-architecture/solution-architecture.md` | **recommend authoring this** |

**Recommend `<dirname>.md`**: it keeps a real, authored document as the section page, and reads as
content rather than scaffolding. But check for a `README.md` first — adding a `<dirname>.md` beside
one has no effect, and the README becomes the section page instead. `confluence-sync-md publish
layout <source>` prints which document actually wins, and under which title, before anything is sent.

A directory with **none** of the three has no page of its own, and its documents are flattened up to
the nearest parent. Only reach for `--keep-hierarchy` if the user wants those directories to become
pages anyway, and tell them the cost first:

- it **writes an `index.md` into every such directory in their source tree**, containing
  `[[_LISTING_]]` (a Confluence children macro). A publish source lives under
  `confluence-content/spaces/`, which `.gitignore` covers in full, so these files appear without
  `git status` ever mentioning them — tell the user they were created, because nothing else will.
- those generated pages have no heading, so they get a machine title like `index [3f9a…]`.

Adding a `<dirname>.md` is almost always the better answer than `--keep-hierarchy`.

## Where the page title comes from

**Front-matter `title:` first; the `# Heading` only when there is no front-matter title.** They are
independent — a document can carry one title in its front-matter and a different heading in its
body, and the page is created under the front-matter one while the heading stays in the body. Every
document in `confluence-macro-md-examples/` is written that way.

The title is the page's whole identity here: it is what the uniqueness check compares, what md2conf
matches an existing page by, and what decides whether a republish updates a page or creates a
second one. So **never infer a page's title from its `# Heading`** — run `publish layout` and read
the title it prints. Two things to tell the user before they edit either string:

- editing the `# Heading` of a document that has a front-matter `title:` changes **nothing** in
  Confluence — same page, same name;
- editing `title:` creates a **new page** on the next publish and leaves the old one behind, because
  there is no stored page ID to rename by.

Two documents with different `# Heading`s still collide if they share a front-matter `title:` — that
is the `page titles are unique` failure below.

## Then run preflight, and show the user what it found

```sh
source .env && uv run --no-sync -- confluence-sync-md publish check --list <source>
```

It checks md2conf is installed, the environment is configured, the space is declared, no two
documents claim the same page title, which documents would overwrite a page the space already has,
and — only for documents that actually contain ` ```mermaid ` or ` ```plantuml ` fences — that those
renderers are present. A missing renderer otherwise raises *during* the publish, after attachments
have already been uploaded.

Add `--local` when the next step is only a `--local` conversion: it then checks what that needs —
`CONFLUENCE_DOMAIN`, no token — instead of the full publish environment. Without the flag, a
token-less shell fails the environment check, which is correct for a publish and wrong for a
conversion. `--offline` keeps the full publish checks but skips the read-only calls to the space.

`--list` prints every document that would be published — md2conf's own selection, `.mdignore`
included, so the list needs no caveat. **Show it to the user before publishing a directory.** A
document marked `(skipped: synchronized: false)` is listed but will not be published; it still
counts for the title check.

## Two checks that stop a publish

**`page titles are unique` failed.** md2conf aborts the whole directory run rather than let two
documents overwrite one page — nothing is uploaded, but nothing is published either. Report which
files collide and ask the user which title should change. Do **not** publish the files one at a time
to route around it: that is how one of them silently overwrites the other.

**`must be deleted in Confluence first` failed.** Those pages already exist and carry attachments,
so a republish 401s mid-run and leaves them stale. `check` prints the page URLs. Give them to the
user and ask them to delete the pages — [the rule](#rules-that-must-not-be-inferred) is that
deleting is a human action here. Never attempt the delete.

A page reported under `will be overwritten` is **not** a failure — it has no attachments and
republishes cleanly. It is still an overwrite, so say so before publishing rather than after: the
user may not know that title is already taken, and md2conf will not warn them.

## Convert locally first, then publish

```sh
source .env && uv run --no-sync -- confluence-sync-md publish convert <source>
source .env && uv run --no-sync -- confluence-sync-md publish apply --under <target-page-url> <source>
```

`--under` takes the URL the user gave and turns it into md2conf's `--root-page`, after
checking its space key against the declaration. A bare page ID works too, but prefer the URL: an ID
carries no space, so nothing can verify it. Omitting `--under` publishes under the space home page —
only do that when the user has explicitly said that is what they want. Every run prints the space,
the parent, and the exact command before doing anything.

Add pass-through options after `--`, for example `-- --keep-hierarchy`. Do not pass `--root-page`
that way; it is refused, because `--under` is what checks the space.

`--local` makes no API calls, so it is the cheap way to see a document convert before any page is
touched. It is **not** a dry run: it writes the `.csf` and any rendered diagrams next to the source
(all gitignored), and it still needs `CONFLUENCE_DOMAIN`, though no token. Read the generated `.csf`
before publishing when the document is new or has changed structurally.

## What the converter can produce

The worked references live in the tool's `templates/` directory, not here. Each documents a
slice of the macro surface with the Markdown that generates it, and the tool's own contract tests
convert them and assert the macros they claim — which is why this skill points at the directory
rather than carrying a copy that nothing would notice going stale.

Ask the tool where it is. The path differs between an editable install and one from an index, and
neither is worth guessing at:

```sh
uv run --no-sync -- confluence-sync-md capabilities --json    # the "templates" key
```

List that directory and read whichever template covers the macro in hand; copy a section from it
rather than recalling the syntax, and copy any adjacent `media/` if the copy keeps an image. The
key reports `(not installed)` when the install shipped without the templates.

They sit outside a space, so `publish convert` refuses them by design. Verify an edit with md2conf
directly against the path above.

Eleven native macros are reachable: `toc`, `children`, `code`, `status`, `info`, `tip`, `note`,
`warning`, `panel`, `expand` and `anchor`. Three points are worth carrying without opening a template:

- **The admonition keyword is not the panel name, and neither is the macro name.** Three registers,
  all different words, so say which one you mean. This is the whole mapping
  (`converter.py:1045-1062`) — seventeen keywords onto four macros:

  | `!!!` keyword | Macro Confluence **stores** | Panel Confluence **displays** |
  |---|---|---|
  | `info`, `note`, `abstract`, `example`, `question`, `quote` | `info` | Info — blue "i" |
  | `success`, `tip`, `hint` | `tip` | Success — green check |
  | `warning`, `attention`, `important` | `note` | Warning — orange "!" |
  | `error`, `danger`, `bug`, `caution`, `failure` | `warning` | Error — red "x" |

  So `!!! tip` and `!!! success` are the same macro, and `!!! note` produces an **Info** panel
  rather than a warning of any kind. **A keyword outside this table is not a surprise panel — it is
  a hard failure**: `DocumentError: unsupported admonition type: <word>`, which aborts the whole
  conversion. Confluence's own **Note** panel is unreachable by any keyword: it needs an
  `ac:adf-extension` tree md2conf does not generate.

  `--use-panel` (below) accepts the same seventeen plus `disclaimer` and `flag`, so those two
  convert only with that flag and fail without it.
- **Every page gets an `info` banner you did not write.** md2conf prepends an `info` macro reading
  "This page has been generated with a tool." above the `<h1>` of every page, by default. It is the
  reason a converted document always emits one more `info` than its Markdown accounts for.
  `--no-generated-by` removes it and `--generated-by MARKDOWN` replaces the wording; both are
  pass-through. Mention it before a first publish — an author who did not expect it reads it as a
  defect.
- **Four flags change what is emitted**, and all are pass-through, so they go after `--`:
  `--use-panel` swaps the four admonition macros for `panel`; `--no-render-latex` emits maths
  macros instead of rasterising formulas to attached images; `--heading-anchors` adds an `anchor`
  to every heading; `--no-generated-by` drops the banner above. Say which one you passed when
  reporting a publish.
- **Anything unmodelled goes through a `csf` fenced block**, which passes Confluence storage format
  through untouched — the route for `pagetree`, `view-file` and third-party app macros. Nothing
  validates it, so a malformed macro fails on the page rather than during conversion.

## Images and attachments change how a page republishes

A local image or a link to a local file is uploaded as a page attachment. That is the single
decision that costs a page its ability to be overwritten later: **a page carrying attachments
cannot be republished without being deleted in Confluence first**, which is a human action. Raise
this *before* adding an image to a document that will be republished, not after the publish fails.

- `![Alt](diagram.png)` embeds and uploads; width and height are read from the file. A standalone
  image also gets a caption from its alt text, so alt text is visible on the page.
- `[Label](report.pdf)` uploads the file and renders a link. A PDF arrives as a link, never as an
  inline preview — the embedded viewer is the `view-file` macro, which needs the `csf` route.
- `![Remote](https://…)` is hotlinked, not uploaded, and creates no attachment.
- **Paths are flattened into the attachment name**, because Confluence attachments have no folders:
  `media/diagram.png` uploads as `media_diagram.png`, and `../shared/report.pdf` as
  `PAR_shared_report.pdf`.
- **Sizing needs inline HTML.** The `{width=120}` attribute syntax is not supported and survives
  into the page as literal text. Use `<img src="…" width="120" height="50" />` — and it must be
  **self-closed**, since a bare `<img …>` aborts the conversion with an XML parse error. Inline
  HTML has to be well-formed XHTML, not merely valid HTML.

## Rules that must not be inferred

- **`source .env` belongs in the same command.** Shell state does not survive between tool calls,
  so `source .env` on its own line does nothing for the next one. A forgotten `source` shows up as
  `Confluence domain not specified`, which reads like a configuration bug and is not.
- **The space comes from `space_key.json`**, never from the directory name and never from
  `CONFLUENCE_SPACE_KEY`, which stays unset. `publish` refuses to run without the declaration.
- **`--skip-update` is always passed**, so nothing is written back into the source. Do not suggest
  `--keep-update`: the page-ID and space-key comments it injects outrank `-s` on every later
  publish, pinning the document to whatever space it first went to.
- **`-s`/`--space`, `--keep-update`, `--api-url`, `-u`/`--username` and `--root-page` are refused**
  in the pass-through, abbreviations included. If a user asks for one, explain which guarantee it
  breaks rather than working around it.
- **The target page decides the space, not `-s`.** md2conf reads the space off the parent page, so a
  target page URL from another space would publish everything there and the declaration would never
  see it. `publish` compares the URL's space key with the declaration and refuses a mismatch —
  never work around that by passing the page ID instead, which cannot be checked.
- **Republishing: stop and ask the user to delete the page in Confluence first.** The token has no
  delete scope, by design and permanently. md2conf tries to trash a superseded attachment mid-publish
  and gets `401 scope does not match`, leaving the page stale — old content plus an orphaned
  attachment. Deleting is a human action here: **never attempt the delete, and never propose adding
  a delete scope to the token.** The procedure is in
  `confluence-content/README.md#republishing-a-page-delete-it-first`.
- **Pages are matched by title, and the title is the front-matter `title:` when there is one** —
  the `# Heading` only otherwise. With no stored page ID, changing that string creates a new page
  and leaves the old one behind, while changing the *other* one does nothing at all. Never report a
  page's title from its heading; run `publish layout` and read what it prints.

## After publishing

Report the page URL and what was created or updated, and say where it landed — the target page the
user named, so they can check it is where they meant. If the run failed partway, say which
attachments were uploaded — a stale page with an orphaned attachment is the expected shape of a
failed republish, not corruption.

## The command surface

Everything this skill does is `confluence-sync-md`, an installed command. `capabilities` states what
it will refuse, as data, and probes what is installed — read it rather than inferring from this file:

```sh
uv run --no-sync -- confluence-sync-md --help
uv run --no-sync -- confluence-sync-md capabilities --json
```

| Command | Does |
|---|---|
| `capabilities` | what the tool can and will not do, plus renderers and declared spaces |
| `space declare URL` | resolve or create the space directory for a target page |
| `space list` | every space declared in this content tree |
| `publish layout SOURCE` | the page tree a source would produce, and which document becomes the parent |
| `publish check SOURCE` | the preflight above |
| `publish convert SOURCE` | convert on disk, no API calls |
| `publish apply SOURCE --under URL` | the publish |

Exit codes are part of the contract: `0` succeeded or every check passed, `1` refused or failed,
`2` the arguments were wrong. `check` returning 1 is what gates a publish.

## Reference

| Topic | Where |
|---|---|
| Tools, install, authentication, md2conf flags | `README.md` |
| Layout, the space rule, republishing, credentials | `confluence-content/README.md` |
| Renderer install and the version-shadowing traps | the tool's `docs/renderers.md` |
| Every native macro, and a publish smoke test | the tool's `templates/`, located by `capabilities --json` |

### Kept in sync by hand

A skill has to be readable on its own, so several rules are stated here *and* elsewhere. Nothing
checks that the copies agree — when one changes, change all of them. Canonical location first:

| Rule | Canonical | Also stated in |
|---|---|---|
| `index.md` / `README.md` / `<dirname>.md` precedence | `confluence-content/README.md#how-the-documents-must-be-organised` | this file; the tool's `capabilities` output |
| Where the page title comes from | `confluence-content/README.md#where-the-page-title-comes-from` | this file; `confluence-macro-md-examples/README.md` |
| Admonition keyword → macro → panel | **this file** | `confluence-macro-md-examples/README.md` (stored names only) — and `make check` prints the macros that directory really emits |
| Delete before republishing | `confluence-content/README.md#republishing-a-page-delete-it-first` | this file; `README.md` |
| What the content root is | the tool's `--help` | this file; `../confluence-export/SKILL.md`; `.env.example` |
| The token is scoped, and the gateway URL | `confluence-content/README.md#the-token-is-a-scoped-token-and-its-prefix-does-not-say-so` | `README.md`; `.env.example` |
| The `python -m` fallback for a quarantined exe | the `confluence-sync-md` tool repo's `docs/user_guide.md#windows-a-quarantined-console-script-exe` | this file; `../confluence-export/SKILL.md` |
