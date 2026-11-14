---
tool: markdownlint-cli2
updated: 2026-11-14
author: Achilleas Voutsas
version: 0.3.0
---

# markdownlint-cli2 — quick start

Lints Markdown against the `markdownlint` rule set and fixes what it can. Configuration-driven: the config file, not the command line, decides rules, globs and ignores. Designed to pair with the VS Code markdownlint extension, which reads the same config files.

## Run

```sh
markdownlint-cli2 "**/*.md" "#node_modules" "#.venv"   # lint the tree
markdownlint-cli2 --fix "**/*.md" "#node_modules"      # apply fixable rules in place
markdownlint-cli2 --config ci/.markdownlint-cli2.jsonc "**/*.md"
cat note.md | markdownlint-cli2 --format > fixed.md    # stdin → fixed stdout
```

## Options

| Option | Effect |
|---|---|
| `glob ...` | globby patterns; `#` or `!` prefix negates; `:` prefix is a literal path; `-` is stdin |
| `--config <file>` | base config from a non-default path |
| `--configPointer <ptr>` | JSON Pointer into `--config`, e.g. `/tool/markdownlint` in `pyproject.toml` |
| `--fix` | rewrite files to resolve fixable issues |
| `--format` | stdin → fixed stdout; ignores globs; never exits `1` |
| `--no-globs` | ignore the config file's `globs` property |

Config files, searched per directory: `.markdownlint-cli2.{jsonc,yaml,cjs,mjs}` (options: `globs`, `ignores`, `gitignore`, `config`, `fix`), then `.markdownlint.{jsonc,json,yaml,yml,cjs,mjs}` (rules only).

Exit codes: `0` no errors · `1` lint errors · `2` the run itself failed.

## Traps

- **A glob that matches nothing passes.** `Linting: 0 files`, exit 0 — so does a mistyped path or an unknown flag (`--version` is read as a glob). In a gate, check the `Linting: N files` line, not just the exit code.
- **Quote every glob.** Unquoted, the shell expands `**/*.md` itself and negations never reach the tool. `#` is the portable negation prefix; `"!…"` works in zsh but bash history-expands it.
- **`markdownlint-cli2 .` lints only the current directory**, not the tree — it is mapped to `*.{md,markdown}`. Use `"**/*.md"`.
- **`.gitignore` is not honoured by default.** In this repo that means `docs/landing-zone/` and every `reference.md` get linted. Set `"gitignore": true` in `.markdownlint-cli2.jsonc` or negate them explicitly.
- **`--fix` writes in place with no backup.** Run without it first; confirm with `git diff --stat`.
- **Exit `2` is not "lint failed".** A gate that treats any non-zero as lint errors misreports a bad config or bad glob.

Docs: [README](https://github.com/DavidAnson/markdownlint-cli2) · full page ingest: [reference.md](reference.md)
