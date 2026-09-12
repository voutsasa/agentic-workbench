# Why these tools, and what each one replaces

## One linter, three concerns

ruff's rule families cover what used to need three tools:

| Family | Replaces |
|---|---|
| `S` | flake8-bandit — the same rules, reimplemented. No separate bandit. |
| `C90` | mccabe complexity. This is the gate; radon is the report. |
| `I` | isort |
| `E`, `F`, `B`, `UP` | pycodestyle, pyflakes, bugbear, pyupgrade |

`D1` is deliberately the only docstring family selected. It enforces that public modules, classes
and functions *have* a docstring; it says nothing about shape. Enabling the rest of `D` will churn
good prose docstrings into a house style and gains nothing — docstrings earn their place by
explaining *why*, and no linter can check that.

## ruff blocks, radon reports

They measure the same thing and that is fine, because they answer different questions. `C901` fails
the build at a line. `radon cc -a` gives an average that moves over time, and `radon mi` gives a
maintainability index — neither is a pass/fail, both are worth watching. If you want radon to fail
too, `xenon` wraps it, but then you are gating the same property twice.

## Where the thresholds come from

Measure, then set. On the project this came from:

- complexity: **7** — the highest any function scores under ruff, so the gate is green the day it
  lands and red the moment anything gets worse. `page_index` and `_subtree` sit exactly at it, and
  the config comment names them.
- coverage: 91% actual, floor at 86. Enough headroom that an honest refactor does not fail CI,
  tight enough that a whole untested module does.

Then ratchet, in its own commit, once the named functions are split.

**A caution learned the hard way.** ruff's C901 and radon's cyclomatic complexity are different
measures, and mixing them produces a gate that does nothing. The same function scored 5 under ruff
and 20 under radon; a gate of 10 "because radon says 20" was three levels looser than anything in
the codebase and could never have failed. Propose the gate from the tool that enforces it.

## uv, and what stays out of the lock file

`uv add --dev` for anything that imports the project or runs constantly: ruff, pyright, pytest,
pytest-cov, pdoc. `uvx` for anything that is a standalone binary run occasionally: pip-audit, radon.
The test is whether the tool needs your dependencies — see traps.md #3.

`[project.scripts]` for anything with a CLI. The alternative is `PYTHONPATH=path/to/src python -m
package`, which then appears in every documented command, every README, and every skill that drives
it — and has to be corrected everywhere when the layout changes.

## The Makefile is the definition of "passing"

One `check` target, and CI runs that target rather than a parallel list of steps. Otherwise the two
drift and "it passes locally" becomes true and useless.

```make
check: lint types test audit complexity docs-current
```

## Documentation: generate what can drift

Hand-written prose about a CLI goes stale the first time a flag changes — reliably, and without
anyone noticing. So:

- the CLI reference renders from the argument parser
- the API reference renders from docstrings
- `make check` regenerates both and fails if the committed copy differs

What stays hand-written is what cannot be derived: what the thing is for, what it refuses to do, and
why the design is the way it is. That is usually a README and one design note.

## Contract tests for what you do not own

When a docstring cites a dependency by file and line — `processor.py:303-310` — that citation is
correct exactly until the next upgrade, and nothing checks it. Pin the behaviour instead:

```python
def test_the_promotion_order_is_index_then_readme_then_dirname() -> None:
    source = inspect.getsource(Processor._index_directory)
    assert source.index('"index.md"') < source.index('"README.md"')
```

Crude, and much better than a paragraph that quietly became false.

Mark the ones that shell out so they can be skipped: `@pytest.mark.slow`, declared in
`[tool.pytest.ini_options]`.
