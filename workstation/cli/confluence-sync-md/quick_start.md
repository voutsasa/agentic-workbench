---
tool: confluence-sync-md
updated: 2026-09-27
author: Achilleas Voutsas
version: 0.4.1
---

# confluence-sync-md — quick start

Moves documents between Markdown and a Confluence Cloud space: `md2conf` publishes and `cme` exports.
This workbench drives it through two skills,
[`confluence-publish`](../../agent/skills/confluence-publish/SKILL.md) and
[`confluence-export`](../../agent/skills/confluence-export/SKILL.md). Use those; this page covers
what they rely on.

**Configure it first.** Each content repository needs a `.env`, plus cme's credential store for
exports: every variable, the token's scopes and the setup commands are in
[`install.md` § Configure](install.md#configure).

## First command

```sh
confluence-sync-md capabilities            # what it can and won't do, and what is installed
confluence-sync-md capabilities --json     # the same, as data; "templates" locates the templates
```

It answers before any content tree exists, and reports what is installed **on this machine**.

## The content tree

Every command acts on a *content root*, the directory holding `spaces/`. It resolves in this order:

1. `--content-root DIR`
2. `$CONFLUENCE_CONTENT_ROOT`
3. the nearest `confluence-content/` at or above the working directory

A directory you name *is* the root, and it must already exist. Trees are created only by
`space declare`, and only after asking.

## Commands

| Command | Does | Reaches Confluence |
|---|---|---|
| `space declare <target-page-url>` | Finds or creates the space directory and its `space_key.json` | first time only |
| `publish layout <source>` | Shows the page tree a source would produce | no |
| `publish check --list <source>` | Checks whether the publish will work and what it touches; exit 1 blocks a publish | yes |
| `publish convert <source>` | Converts to Confluence Storage Format on disk | no |
| `publish apply --under <target-page-url> <source>` | Publishes | yes |
| `export preview --verb <verb> <url>` | Shows where an export would land, and prints the `cme` command | yes |

Prefix every command that reaches Confluence with `source .env &&`, in the same shell call.

## Traps

- **It never deletes in Confluence, and never runs `cme` itself.** The token has no delete scope. An
  export writes into the working directory, so a person approves the destination and runs the
  printed command.
- **Exit code 2 means wrong arguments**, and **1 from `check`** is the result that should stop a
  publish.
- **A page with attachments can't be republished** until someone deletes it in Confluence. The
  `confluence-publish` skill covers this.
