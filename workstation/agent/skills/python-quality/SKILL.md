---
name: python-quality
description: Apply quality gates to a Python project — ruff, pyright, pytest with a coverage floor, radon, dependency audit, and generated documentation — with thresholds derived from the code as it is rather than imposed on it. Use when asked to set up or improve linting, type checking, static analysis, complexity, test coverage, docs generation or uv project structure, on a new project or an existing one. Not for reviewing code — that is `review`.
author: Achilleas Voutsas
version: 0.3.0
---

# Python quality gates

Gates that get switched off are worse than no gates. The rule that keeps them on:

> **Thresholds start where the code is, then ratchet.**

Set complexity to the tightest value that is *green today* — the highest complexity any function
currently has — and name the functions sitting at it. Set the coverage floor a few points under
actual. A gate that opens red teaches everyone to pass `--no-verify`; a gate with slack in it hides
the next regression.

## Phase 1 — Measure, write nothing

```sh
uv run python <skill>/scripts/measure.py [PATH]
```

It runs ruff, pyright, pytest with coverage and radon against the project as it stands, and
proposes thresholds derived from what it found. Nothing is written in this phase.

If a tool is not installed yet, it reports that rather than installing it — what to add is the
user's decision in phase 2.

## Phase 2 — Show the proposal and stop

Show a table: **current → proposed → what fails at this level**, and name the functions that will
fail. Then stop and let the user approve or adjust.

Say plainly where each number came from: "complexity 7 — the highest any function scores today, so
nothing fails; `page_index` and `_subtree` sit exactly there, and one more branch in either turns
the build red." The ratchet is a follow-up, not a compromise to hide.

**Measure complexity with ruff, never radon.** They count differently — on the project this came
from, radon scored a function 20 where ruff scored it 5. ruff is what gates, so ruff's number is the
only one that can set the gate; radon's average is a trend line beside it.

## Phase 3 — Apply

Copy from `templates/`, adjusting the thresholds to the approved numbers:

| File | From |
|---|---|
| `pyproject.toml` blocks | `templates/pyproject.md` |
| `Makefile` | `templates/Makefile` |
| `.github/workflows/check.yml` | `templates/check.yml` |
| `docs` generators, if the project has a CLI or a public API | `templates/cli_reference.py` |
| link gate, if the project is mostly prose | `templates/check_links.py` |

Dependencies: `uv add --dev ruff pyright pytest pytest-cov` — and `pdoc` too if docs are generated,
because it imports the code it documents and so cannot run under `uvx`. Leave `pip-audit` and
`radon` on `uvx`, so they never enter the lock file.

Prefer `[project.scripts]` over `python -m` for anything with a CLI. A console script removes the
`PYTHONPATH=…` prefix that otherwise infects every documented command.

## Phase 4 — Close the loop, honestly

Run `make check`. Report what it found, including anything still red. The first run is where this
skill earns its keep: expect real findings, and expect at least one to be a missing test rather than
a style nit — an unused import in a test file usually means a function nobody covers.

Fix the mechanical ones (`ruff check --fix`, `ruff format`). For each remaining one, decide with the
user rather than silencing it. When a rule must be suppressed, the `noqa` carries the reason:

```python
# S603: the argument list is built from validated inputs, never a shell string.
return subprocess.run(command, check=False).returncode  # noqa: S603
```

**Never report a gate as passing without running it.** Quote the output.

## The tools, and what each replaces

| Concern | Tool | Note |
|---|---|---|
| Lint, format, security, complexity | **ruff** — `E,F,I,B,UP,S,C90,D1` | no separate bandit, no separate complexity gate |
| Types | **pyright**, run as the project venv interpreter with `-m pyright`, with `venvPath` and `venv` set | the module route avoids a blocked Windows console launcher; without those two lines it resolves against the system interpreter and calls every third-party import missing |
| Complexity trend | **radon**, advisory only | ruff blocks, radon reports what a gate cannot |
| Dependency CVEs | **`uvx pip-audit`** | the one thing ruff's `S` rules do not cover |
| Docstrings | **`D1` only** | enforce that they exist; never dictate their shape |

## References

Three files, none of them loaded unless you need them:

| File | Read it when |
|---|---|
| `references/traps.md` | **Before phase 1, always.** Five failure modes that report success while being wrong; two silently weaken the gates you just installed. |
| `references/decisions.md` | Why each tool, where the thresholds came from, what stays out of the lock file, and how documentation and contract tests are gated. |
| `references/design-rules.md` | The work is structural rather than mechanical — five rules about abstractions, layer boundaries and explicit inputs. |

## Scripts

| Script | Does |
|---|---|
| `scripts/measure.py` | reports current lint, type, coverage and complexity state, and proposes thresholds. Read-only. |
| `tests/test_measure.py` | `<venv-python> -m unittest discover -s tests -t tests`, where `<venv-python>` is the project's `.venv/bin/python` (macOS) or `.venv\Scripts\python.exe` (Windows) — stdlib only, no dependencies. |
