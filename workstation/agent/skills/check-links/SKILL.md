---
name: check-links
description: Check that the relative links in Markdown files resolve — each linked file or folder exists, and each #anchor into a Markdown file matches a heading (GitHub slug rules) or an HTML id. Use when asked to check, verify or fix links in a README or docs, or after editing, moving or renaming Markdown files or headings. Deterministic and offline; does not fetch external URLs.
author: Achilleas Voutsas
version: 0.6.2
---

# Check links

One script does the work. This file says only when to run it and what to do with its output.

## Run

From the calling project's root, with its venv interpreter:

```sh
uv run --no-sync python <skill>/scripts/check_links.py README.md docs/
uv run --no-sync python <skill>/scripts/check_links.py --json README.md
```

`<skill>` is this folder. A folder argument is searched for `*.md`, without `.git`, `.venv`,
`node_modules` and `__pycache__`. Before a project has a venv, run the script with `python3` on
macOS or `python` on Windows: it is stdlib only.

| Exit | Meaning |
|---|---|
| 0 | Every relative link resolves |
| 1 | At least one link is broken. Each one prints as `path:line: missing file|missing anchor: target` |
| 2 | An argument is not a file or a folder |

## What it checks, and what it does not

| Checked | Not checked |
|---|---|
| Inline links, images and reference definitions with a relative target | External URLs (`https:`, `mailto:`, `//host`). Use `verify-docs --online` for those |
| That the target file or folder exists, after `%20`-style decoding | Anchors into non-Markdown files, such as `code.py#L10` |
| That a `#fragment` into a `.md` file matches an ATX heading slug, `-1`/`-2` for repeats, or an HTML `id`/`name` | Setext headings (underlined with `===` or `---`) |
| Nothing inside fenced or inline code | Whether the link text describes the target |

## Fixing what it reports

- **Missing file:** find where the target moved with `git log --follow --name-status -- <old path>`. Then repoint the link. Do not create a file only to satisfy a link.
- **Missing anchor:** the heading was probably renamed. Search the target for the heading and repoint the fragment to its new slug. A changed heading breaks inbound links in other files too, so re-run on the whole folder.
- Report every link you could not repoint with confidence instead of guessing.

Tests: `uv run --no-sync python -m unittest discover -s <skill>/tests -t <skill>/tests`.
