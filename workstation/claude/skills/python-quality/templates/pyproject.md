# pyproject.toml blocks

Paste these in and set the two thresholds to the numbers phase 1 measured. The comments explaining
*why* a threshold is where it is are not decoration — they are what stops someone tightening it
back to an ideal and turning the gate off.

```toml
[dependency-groups]
dev = [
    "pdoc>=16",          # only if docs are generated; it imports your code, so it cannot be uvx
    "pyright>=1.1.411",
    "pytest>=9",
    "pytest-cov>=7",
    "ruff>=0.16",
]

[project.scripts]
your-command = "your_package.cli:main"   # a console script, not `python -m` + PYTHONPATH

[tool.ruff]
# Set to fit the code that exists rather than to force a reformat: measure the longest lines first.
line-length = 120
src = ["src"]

[tool.ruff.lint]
# E/F/I/B/UP: correctness and modern idiom. S: flake8-bandit, which is why there is no separate
# bandit. C90: mccabe, the complexity gate. D1: docstrings must EXIST — their shape is deliberately
# not policed.
select = ["E", "F", "I", "B", "UP", "S", "C90", "D1"]
ignore = [
    "D107",  # __init__ docstring: the class docstring already says it
    "E501",  # line length is enforced by the formatter, not twice
]

[tool.ruff.lint.mccabe]
# <N> rather than 8, because at 8 <k> functions fail and at <N> exactly <j> do: <names>.
# Ratchet down once those are split.
max-complexity = <N>

[tool.ruff.lint.per-file-ignores]
"**/test_*.py" = ["S101", "D103", "D100"]  # assert is the point of a test; names carry the intent
"**/conftest.py" = ["D100"]

[tool.pyright]
# Without these two, pyright resolves against the system interpreter and reports every third-party
# import as missing — a wall of false positives that trains everyone to ignore it.
venvPath = "."
venv = ".venv"
include = ["src", "tests"]
typeCheckingMode = "standard"     # "strict" once the public API is stable

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "slow: shells out to a real binary",
]

[tool.coverage.run]
source = ["src/your_package"]
omit = ["*/__main__.py"]

[tool.coverage.report]
exclude_also = ["if TYPE_CHECKING:", "raise NotImplementedError"]
```

The coverage floor lives in the `Makefile` next to the command that enforces it:
`--cov-fail-under=<measured minus a few points>`.
