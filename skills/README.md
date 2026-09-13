# Skills — this repo's own

Skills whose procedure is **specific to this workbench**: they name `SOURCES.md`, `docs/landing-zone/`
or the `workstation/` tree, so they would be wrong in any other repo.

That is the line against [`../workstation/agent/skills/`](../workstation/agent/skills/), which holds
the **global** skills, linked into `~/.claude/skills/` by
[`../workstation/scripts/link_config.py`](../workstation/scripts/link_config.py) and shared unmodified
by every machine — its `SKILLS` tuple is the authoritative list. A skill earns promotion there by
being register-free: a caller supplies whatever this repo would have decided. Until it is, it stays
here.

`fetch-to-markdown` was promoted out of this folder on 2026-09-13 — it was the routing and conversion
half of `ingest-source`, and takes its destination path from the caller.

| Skill | What it does |
|---|---|
| [`ingest-source/`](ingest-source/) | Pull one `SOURCES.md` entry into the corpus: resolve the destination, delegate the conversion to the global `fetch-to-markdown`, record |

## Loading them

**Claude Code discovers `.claude/skills/`, not this folder.** These are versioned here and linked
across, so the skill loads while the source of truth stays in the tracked tree — this repo authors
skills as a deliverable, which is the reason for the second tree. A repo that merely *uses* a skill
should write it straight into `.claude/skills/` and skip the link.

```sh
mkdir -p .claude/skills
ln -s ../../skills/ingest-source .claude/skills/ingest-source
```

`fetch-to-markdown` needs no line here — it is global, and `link_config.py --apply` puts it in
`~/.claude/skills/` where every repo sees it.

Per-clone, like the pre-push hook, and never tracked — `.claude/` is gitignored, added on
2026-09-13 when it turned out it never had been and the link was simply absent. Tracking the link
itself is not the alternative: it is a symlink on macOS and a junction on Windows, so a fresh clone
has to re-run the command above.

## Conventions

Same shape as the global skills, so a promotion is a move rather than a rewrite:

```
<skill>/SKILL.md           name: must equal the folder name, or it does not load
<skill>/references/        loaded on demand, for branches most runs never take
<skill>/scripts/           stdlib-only, so they run before any venv exists
<skill>/tests/             unittest; python3 -m unittest discover -s skills/<skill>/tests
```
