# Skills — this repo's own

Skills whose procedure is **specific to this workbench**: they name `SOURCES.md`, `docs/landing-zone/`
or the `workstation/` tree, so they would be wrong in any other repo.

That is the line against [`../workstation/agent/skills/`](../workstation/agent/skills/), which holds
the **global** skills — `review`, `python-quality`, `verify-docs`, `fix-findings` — linked into
`~/.claude/skills/` and shared unmodified by every machine. A skill earns promotion there by working in
a repo that is not this one; until it has, it stays here.

| Skill | What it does |
|---|---|
| [`ingest-source/`](ingest-source/) | Pull one `SOURCES.md` entry into the corpus: resolve the destination, delegate the conversion, record |
| [`fetch-to-markdown/`](fetch-to-markdown/) | One URL and one destination path to clean markdown: classify, route, convert, quality-check |

**`fetch-to-markdown` is a promotion candidate, not a repo-local skill.** It names no register, no
corpus directory and no `workstation/` path — the caller supplies the destination — so it is here only
until it has been used from a repo that is not this one. `ingest-source` is what keeps the
workbench-specific half: where an entry lands, what its file is called, and what gets written back.

## Loading them

**Claude Code discovers `.claude/skills/`, not this folder.** These are versioned here and linked
across, so the skill loads while the source of truth stays in the tracked tree:

```sh
mkdir -p .claude/skills
ln -s ../../skills/ingest-source .claude/skills/ingest-source
ln -s ../../skills/fetch-to-markdown .claude/skills/fetch-to-markdown
```

**Both, or neither works as intended.** `ingest-source` delegates its conversion to
`fetch-to-markdown`; with only the first linked, the delegation resolves to a file the agent has to be
told to read rather than a skill it discovers.

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
