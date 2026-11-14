---
tool: sem-cli
updated: 2026-08-24
author: Achilleas Voutsas
version: 0.4.2
---

# sem-cli — quick start

Semantic version control: diff, blame and impact analysis at the level of **entities** — functions, classes, types — rather than lines. Works across many languages. Use it when the question is "what actually changed and what depends on it", which line diffs answer badly.

## Common invocations

```
sem diff                              # semantic diff; takes git diff syntax
sem impact <entity>                   # deps, dependents, transitive impact, tests
sem blame <path>                      # who last modified each entity
sem entities <path>                   # list entities under a file or directory
```

`sem diff` excludes untracked files, matching git's behaviour.

## Subcommands

| Command | Use |
|---|---|
| `diff` | semantic diff of changes |
| `impact` | blast radius of changing one entity, including affected tests |
| `find` | locate an entity definition by name |
| `callers` | who calls or references an entity |
| `refs` | what an entity calls or references |
| `grep` | text search, `rg`-compatible `file:line:text` output |
| `graph` | full entity dependency graph |
| `blame` | per-entity last modifier |
| `log` | one entity's evolution; with no entity, repo hotspots and co-change pairs |
| `entities` | enumerate entities under paths |
| `context` | token-budgeted context for an entity — built for feeding an agent |
| `stats` | lifetime diff statistics |
| `xref` | cross-repo dependencies across indexed repos; needs `sem login` |
| `mcp` | run as an MCP server over stdio |
| `setup` / `unsetup` | replace `git diff` globally with `sem diff`, and undo it |

## Worth knowing

- **`sem context` is the agent-facing one.** It returns an entity's context under a token budget, which is why it fits this repo's interest in context engineering.
- **`sem log` with no argument is a repo analysis**, not a commit list — it reports hotspots and files that change together.
- **`sem setup` changes global git behaviour.** It rewires `git diff` for every repo on the machine. `sem unsetup` restores it.
- **Cloud is off until enabled.** `login`, `cloud` and `xref` are opt-in; telemetry is local by default with nothing uploaded. `xref` (cross-repo dependencies) is the one capability that does require `sem login`.

Docs: [Documentation](https://ataraxy-labs.github.io/sem/) · full page ingest: [reference.md](reference.md)
