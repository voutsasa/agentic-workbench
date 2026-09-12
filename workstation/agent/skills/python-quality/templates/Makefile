# Every gate this project applies, in one place, so `make check` and CI cannot disagree.
#
# ruff blocks, radon reports: the complexity gate is ruff's C901, set to the value phase 1
# measured rather than to an ideal, and radon gives the trend a gate cannot. pip-audit and radon run through uvx so they never enter the lock
# file. Docs are regenerated and the diff checked, because prose describing a CLI always drifts.

PY := .venv/bin
SRC := src tests

# From phase 1: measured coverage minus a few points. Deliberately has no default —
# a floor nobody measured is the failure this skill exists to prevent, and an unset
# variable fails loudly where a plausible-looking 85 would not.
COVERAGE_FLOOR := <measured minus a few points>

.PHONY: check lint format types test audit complexity docs docs-current all

check: lint types test audit complexity docs-current

lint:
	$(PY)/ruff check $(SRC)
	$(PY)/ruff format --check $(SRC)

format:
	$(PY)/ruff check $(SRC) --fix
	$(PY)/ruff format $(SRC)

types:
	$(PY)/pyright

test:
	$(PY)/python -m pytest -q --cov=your_package --cov-report=term-missing --cov-fail-under=$(COVERAGE_FLOOR)

audit:
	uvx pip-audit

complexity:
	uvx --python 3.14 radon cc src -a -nb
	uvx --python 3.14 radon mi src -nb || true

docs:
	$(PY)/python -m your_package.reference > docs/cli.md
	$(PY)/pdoc -o docs/api your_package

docs-current: docs
	@git add --intent-to-add docs/
	@git diff --exit-code docs/ \
	  || (echo "docs are stale — run 'make docs' and commit the result"; exit 1)
