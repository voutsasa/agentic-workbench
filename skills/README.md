# Skills — this repo's own

Skills whose procedure is **specific to this workbench**: they name `SOURCES.md`, `docs/landing-zone/`
or the `workstation/` tree, so they would be wrong in any other repo.

That is the line against [`../workstation/agent/skills/`](../workstation/agent/skills/), which holds
the **global** skills — `review`, `python-quality`, `verify-docs`, `fix-findings` — linked into
`~/.claude/skills/` and shared unmodified by every machine. A skill earns promotion there by working in
a repo that is not this one; until it has, it stays here.

| Skill | What it does |
|---|---|
| [`ingest-source/`](ingest-source/) | Pull one `SOURCES.md` entry into the corpus: classify, route, convert, quality-check, record |

## Loading them

**Claude Code discovers `.claude/skills/`, not this folder.** These are versioned here and linked
across, so the skill loads while the source of truth stays in the tracked tree:

```sh
mkdir -p .claude/skills
ln -s ../../skills/ingest-source .claude/skills/ingest-source
```

Per-clone, like the pre-push hook, and never tracked — `.claude/` is not in git. A fresh clone has to
re-run it.

## Conventions

Same shape as the global skills, so a promotion is a move rather than a rewrite:

```
<skill>/SKILL.md           name: must equal the folder name, or it does not load
<skill>/references/        loaded on demand, for branches most runs never take
<skill>/scripts/           stdlib-only, so they run before any venv exists
<skill>/tests/             unittest; python3 -m unittest discover -s skills/<skill>/tests
```
