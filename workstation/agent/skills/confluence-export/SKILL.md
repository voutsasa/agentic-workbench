---
name: confluence-export
description: Retrieve pages, subtrees or whole spaces from Confluence Cloud into this repository as Markdown, using cme. Use whenever the user asks to export, fetch, pull or retrieve Confluence content. Previews the destination and the resulting directory structure for approval before fetching anything. Not for sending Markdown to Confluence — that is confluence-publish.
author: Achilleas Voutsas
version: 0.4.0
---

# Exporting Confluence pages to Markdown

`cme` is the retrieval counterpart to md2conf; md2conf has no export path at all. An export is a
**cache** of what Confluence already holds, not source — `confluence-content/spaces/*/export/` is
gitignored, so nothing in it is backed up by this repository.

**Which `confluence-sync-md` runs.** Every command below is `uv run --no-sync -- confluence-sync-md`: in a
repository that pins the tool (`uv add`), that is the pinned copy in its `.venv`; anywhere else it is
the global install from `workstation/cli/confluence-sync-md/install.md`. `--no-sync` keeps it from
installing or updating anything in the repository, and `--` ends uv's own options.

## Every verb takes a URL, never a space key

This has already gone wrong once here. Copy the URL from the browser.

| Verb | Use it for |
|---|---|
| `pages` | one page, nothing below it |
| `pages-with-descendants` | a page and its whole subtree |
| `spaces` | an entire space |
| `orgs` | every space in the organisation |

Reach for `pages-with-descendants` when the page is an index built on a `children` macro — decision
logs and ADR registers usually are. Its entries are child pages, not links in the text, so
exporting the index alone yields a near-empty document.

## Where the commands act

On a **content root** — the directory holding `spaces/`, which in this repository is
`confluence-content/` itself. It is an input, not something the tool infers about itself:
`--content-root DIR`, else `$CONFLUENCE_CONTENT_ROOT`, else the nearest `confluence-content/` at or
above the working directory. A directory you name **is** the root, so `--content-root ~/docs` means
`~/docs/spaces/<Space>/`. Running from inside this repository needs none of them, and
`capabilities --json` reports the root it resolved — check it there rather than assuming, because
the root is what decides which `space_key.json` declarations the preview can match a URL against.

## Preview before fetching, and get it approved

```sh
source .env && uv run --no-sync -- confluence-sync-md export preview --verb pages-with-descendants <url>
```

This resolves the URL's space key against the `space_key.json` declarations and prints:

- the **target location** — which declared space the URL belongs to, and the `export/` directory it
  will land in
- the **current state** of that directory — missing, empty, or holding a `confluence-lock.json`
  from a previous run, which means the next run is incremental
- the **directory structure** the export will produce, with the real ancestor titles resolved
- the exact `mkdir -p`, `cd` and `cme` command

It **never runs `cme`**. Show the preview to the user and get approval for the destination and the
tree before running the printed command. `--offline` skips the two read-only API calls that resolve
the layout and shows the path templates unresolved.

If no space directory declares the URL's key, the script fails and lists the keys that do exist.
That is the guard against a 12 MB export landing in the wrong tree — do not work around it by
running `cme` from somewhere else. Create the space directory and its `space_key.json` first.

## Running the export

Run the command exactly as previewed. Two details in it are load-bearing:

- The preview names `cme` by its **absolute path**, the copy installed beside the interpreter
  `confluence-sync-md` runs under, so it still resolves after the `cd` leaves the repo root.
- `cme` writes to the current directory, which is why the command `cd`s into the space's `export/`
  directory. Nothing enforces this — the convention holds only because it is followed.

The BIAD subtree takes about a minute for 31 pages and 57 attachments.

## If the exe fails to spawn with Access is denied

A Windows Defender/EDR quarantine of the console-script `.exe` the chosen `confluence-sync-md`
install resolved to, not a permissions bug — full diagnosis and the substitute commands are in the
`confluence-sync-md` tool repo's `docs/user_guide.md#windows-a-quarantined-console-script-exe`.
Short version: substitute `<path-to-that-install>\python.exe -m confluence_sync_md <args>` for
`confluence-sync-md <args>`, and `... -m confluence_markdown_exporter.main <args>` for the printed
`cme <args>` — `cme` has no package-level `__main__.py`.

## Rules that must not be inferred

- **`source .env` belongs in the same command** as everything else — shell state does not survive
  between tool calls. It is also what exports `CME_CONFIG_PATH`, and it must be set before the
  *first* `cme` command or the credential store is created in the wrong place.
- **`cme` does not read `.env`.** It keeps its own credential store at `CME_CONFIG_PATH`, holding
  the same token. The path must be absolute: `cme` resolves it against the working directory, and
  exports run from inside `export/`.
- **Never print the token.** `cme config list` shows `api_token` in plaintext — use the read-back
  snippet in `confluence-content/README.md#setting-the-credentials` instead.
- **Changing a path template invalidates the lock file.** `skip_unchanged` compares versions, not
  paths, so a re-run after a template change writes pages to new locations while leaving every
  attachment at the old one, and `cleanup_stale` does not remove the strays. Delete the lock file
  and the exported tree, then export again from empty.
- **An export is not a staging area for `publish/`.** Macros without a Markdown equivalent, and
  images that arrive as attachment files rather than the Mermaid or PlantUML source they were
  rendered from, will not republish as they came. Anything worth keeping belongs under `publish/`
  or outside `confluence-content/`.
- **Breadcrumb links point outside a subtree export.** `pages-with-descendants` exports ancestors as
  directories only, not as documents, so links to them resolve to files that were never fetched.
  Export the whole space if those links must land.

## Reference

| Topic | Where |
|---|---|
| Verbs, layout, credentials, the lock file | `confluence-content/README.md` |
| What `cme` handles, and why not the REST API's own Markdown | `README.md` |

### Kept in sync by hand

A skill has to be readable on its own, so some rules are stated here *and* elsewhere, with nothing
checking that the copies agree. When one changes, change all of them:

| Rule | Canonical | Also stated in |
|---|---|---|
| What the content root is | the tool's `--help` | this file; `../confluence-publish/SKILL.md`; `.env.example` |
| The `python -m` fallback for a quarantined exe | the `confluence-sync-md` tool repo's `docs/user_guide.md#windows-a-quarantined-console-script-exe` | this file; `../confluence-publish/SKILL.md` |
| `CME_CONFIG_PATH` must be absolute, and set before the first `cme` | `confluence-content/README.md#credentials` | this file; `.env.example` |
| A template change invalidates the lock file | `confluence-content/README.md#changing-a-path-template-invalidates-the-lock-file` | this file |
| Breadcrumb links point outside a subtree export | `confluence-content/README.md#what-an-export-produces` | this file |
